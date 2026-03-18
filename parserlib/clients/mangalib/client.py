import asyncio
import re

from msgspec.json import decode
from pyrate_limiter import Duration, Limiter, Rate
from pyrate_limiter.extras.aiohttp_limiter import RateLimitedSession

from parserlib.clients.mangalib.structs import Chapter, ChapterData, Manga, MangaChapter, MangaChapters, MangaData
from parserlib.core.base_client import BaseClient
from parserlib.core.exceptions import SlugNotFound
from parserlib.core.models import ChapterEntry, ChunkGroup, FetchPlan, ImageChunk, WorkDescriptor

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0',
    'Accept': '*/*',
    'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
    'Site-Id': '1',
    'X-DL-Service': 'mangalib',
    'Content-Type': 'application/json',
    'Client-Time-Zone': 'Europe/Moscow',
    'Referer': 'https://mangalib.me/',
    'Origin': 'https://mangalib.me',
    'Sec-GPC': '1',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'Connection': 'keep-alive'
}

class MangalibClient(BaseClient):
    NAME = "Mangalib parser"
    base_url = [
        "mangalib.me",
        "mangalib.org"
    ]

    def __init__(self):
        self.client = RateLimitedSession(
            Limiter(
                Rate(
                    limit=90,
                    interval=Duration.MINUTE
                ),
            ),
            headers=HEADERS
        )

        self.api_url = "https://api.cdnlibs.org/api/manga"
        self.image_url = "https://img3.mixlib.me"

    async def _request_bytes(self, url: str) -> bytes:
        resp = await self.client.get(url)
        resp.raise_for_status()
        return await resp.read()

    async def _get_manga(self, slug: str) -> MangaData:
        raw = await self._request_bytes(f"{self.api_url}/{slug}?fields[]=teams")
        return decode(raw, type=Manga).data

    async def _get_chapters(self, slug: str) -> list[Chapter]:
        raw = await self._request_bytes(f"{self.api_url}/{slug}/chapters")
        return decode(raw, type=MangaChapters).data
    
    async def _get_chapter_data(self, slug: str, key: str) -> ChapterData:
        raw = await self._request_bytes(f"{self.api_url}/{slug}/chapter?{key}")
        return decode(raw, type=MangaChapter).data
    
    async def _get_image(self, url: str) -> bytes:
        return await self._request_bytes(f"{self.image_url}{url}")

    async def inspect(self, url: str) -> WorkDescriptor:
        result = re.search(
            r"mangalib\.(?:me|org)/\w+/(?:manga/)?(\d+--[a-z_-]+)",
            url
        )

        if not result:
            raise SlugNotFound
        
        slug = result.group(1)

        manga_data, chapters = await asyncio.gather(
            self._get_manga(slug),
            self._get_chapters(slug)
        )

        return WorkDescriptor(
            title=manga_data.rus_name,
            slug=slug,
            source_url=url,
            chapters=[
                chapter.into_core()
                for chapter
                in chapters
            ]
        )

    async def _fetch(self, plan: FetchPlan) -> list[ChunkGroup]:
        slug = plan.work.slug

        selected_chapters = plan.work.chapters[
            plan.from_chapter:plan.to_chapter + 1
        ]

        async def fetch_chapter(chapter: ChapterEntry) -> ChunkGroup:
            chapter_data = await self._get_chapter_data(slug, chapter.key)

            async def fetch_page(page_index: int, page) -> ImageChunk:
                payload = await self._get_image(page.url)

                return ImageChunk(
                    id=page_index,
                    payload=payload,
                )

            page_tasks = [
                fetch_page(i, page)
                for i, page in enumerate(chapter_data.pages)
            ]

            chunks = await asyncio.gather(*page_tasks)

            chunks.sort(key=lambda chunk: chunk.id)

            return ChunkGroup(
                id=chapter.id,
                chunks=chunks
            )

        chapter_tasks = [fetch_chapter(chapter) for chapter in selected_chapters]
        groups = await asyncio.gather(*chapter_tasks)

        groups.sort(key=lambda group: group.id)
        return groups
        
    async def close(self):
        session = getattr(self.client, "_session", None)
        if session is not None and not session.closed:
            await session.close()