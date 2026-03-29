import asyncio
import re

from msgspec.json import decode
from selectolax.lexbor import LexborHTMLParser

from parserlib.clients.mangalib.structs import Chapter, Manga, MangaChapters, MangaData
from parserlib.clients.ranobelib.structs import ChapterData, RanobeChapter
from parserlib.core.base_client import BaseClient
from parserlib.core.callback import ProgressCallback
from parserlib.core.exceptions import SlugNotFound
from parserlib.core.http_client import HttpClient
from parserlib.core.models import ChapterEntry, ChunkGroup, DataChunk, FetchPlan, ImageChunk, TextChunk, WorkDescriptor

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0',
    'Accept': '*/*',
    'Accept-Language': 'ru,en-US;q=0.9,en;q=0.8',
    'Site-Id': '3',
    'X-DL-Service': 'ranobelib',
    'Content-Type': 'application/json',
    'Client-Time-Zone': 'Europe/Moscow',
    'Referer': 'https://ranobelib.me/',
    'Origin': 'https://ranobelib.me',
    'Sec-GPC': '1',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'Connection': 'keep-alive'
}

class RanobelibClient(BaseClient):
    NAME = "Ranobelib parser"
    base_url = [
        "ranobelib.me"
    ]

    def __init__(self):
        self.http = HttpClient(headers=HEADERS)

        self.api_url = "https://api.cdnlibs.org/api/manga"

    async def _request_bytes(self, url: str) -> bytes:
        return await self.http.request_bytes(url)

    async def _get_ranobe(self, slug: str) -> MangaData:
        raw = await self._request_bytes(f"{self.api_url}/{slug}?fields[]=teams")
        return decode(raw, type=Manga).data

    async def _get_chapters(self, slug: str) -> list[Chapter]:
        raw = await self._request_bytes(f"{self.api_url}/{slug}/chapters")
        return decode(raw, type=MangaChapters).data
    
    async def _get_chapter_data(self, slug: str, key: str) -> ChapterData:
        raw = await self._request_bytes(f"{self.api_url}/{slug}/chapter?{key}")
        return decode(raw, type=RanobeChapter).data
    
    async def _get_image(self, url: str) -> bytes:
        return await self._request_bytes(url)
    
    async def _parse_html_to_chunks(self, html: str) -> list[DataChunk]:
        parser = LexborHTMLParser(html)
        chunks = []
        chunk_id = 0
    
        for node in parser.root.traverse():
            if node.tag == "p":
                text = node.text(strip=True)
                if text:
                    chunks.append(TextChunk(id=chunk_id, text=text))
                    chunk_id += 1
    
            elif node.tag == "img":
                src = node.attributes.get("src", "")
                if src:
                    payload = await self._get_image(src)
                    if payload:
                        chunks.append(
                            ImageChunk(
                                id=chunk_id,
                                payload=payload
                            )
                        )
                    chunk_id += 1
    
        return chunks
    
    def _extract_text_from_prosemirror_node(self, node: dict) -> str:
        node_type = node.get("type", "")
    
        if node_type == "text":
            return node.get("text", "")
    
        if node_type == "hardBreak":
            return "\n"
    
        parts = []
        for child in node.get("content", []):
            parts.append(self._extract_text_from_prosemirror_node(child))
        return "".join(parts)
    
    async def _parse_prosemirror_to_chunks(self, doc: dict) -> list[DataChunk]:
        chunks = []
        chunk_id = 0
    
        for node in doc.get("content", []):
            node_type = node.get("type", "")
    
            if node_type == "paragraph":
                text = self._extract_text_from_prosemirror_node(node).strip()
                if text:
                    chunks.append(TextChunk(id=chunk_id, text=text))
                    chunk_id += 1
    
            elif node_type == "image":
                src = node.get("attrs", {}).get("src", "")
                if src:
                    payload = await self._get_image(src)
                    if payload:
                        chunks.append(
                            ImageChunk(
                                id=chunk_id,
                                payload=payload
                            )
                        )
                    chunk_id += 1

        return chunks

    async def inspect(self, url: str) -> WorkDescriptor:
        result = re.search(
            r"ranobelib\.me/\w+/(?:book/)?(\d+--[a-z_-]+)",
            url
        )

        if not result:
            raise SlugNotFound
        
        slug = result.group(1)

        ranobe_data, chapters = await asyncio.gather(
            self._get_ranobe(slug),
            self._get_chapters(slug)
        )

        return WorkDescriptor(
            title=ranobe_data.rus_name,
            slug=slug,
            source_url=url,
            chapters=[
                chapter.into_core()
                for chapter
                in chapters
            ]
        )

    async def _fetch(self, plan: FetchPlan, progress_callback: ProgressCallback) -> list[ChunkGroup]:
        slug = plan.work.slug

        selected_chapters = plan.work.chapters[
            plan.from_chapter:plan.to_chapter + 1
        ]

        chapters_count = len(selected_chapters)

        async def fetch_chapter(idx: int, chapter: ChapterEntry) -> ChunkGroup:
            chapter_data = await self._get_chapter_data(slug, chapter.key)

            content = chapter_data.content

            if isinstance(content, str):
                chunks = await self._parse_html_to_chunks(content)
            elif isinstance(content, dict):
                chunks = await self._parse_prosemirror_to_chunks(content)
            else:
                print(f"Something went wrong on chapter with id = {idx}")
                chunks = []

            progress_callback(idx, chapters_count, chapter.title)

            return ChunkGroup(
                id=chapter.id,
                title=chapter.title,
                chunks=chunks
            )

        groups = []

        for i, chapter in enumerate(selected_chapters):
            res = await fetch_chapter(i, chapter)
            groups.append(res)

        groups.sort(key=lambda group: group.id)
        return groups
        
    async def close(self):
        await self.http.close()