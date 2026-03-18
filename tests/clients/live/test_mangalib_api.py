import pytest

from parserlib.clients.mangalib.client import MangalibClient
from parserlib.core.models import FetchPlan

@pytest.fixture
def manga_url() -> str:
    return "https://mangalib.me/ru/manga/1064--kono-subarashii-sekai-ni-shukufuku-o"

@pytest.mark.api
@pytest.mark.asyncio
async def test_mangalib_live_inspect_contract(manga_url):
    client = MangalibClient()
    try:
        work = await client.inspect(manga_url)
    finally:
        await client.close()

    assert work.slug
    assert work.title
    assert work.source_url == manga_url
    assert isinstance(work.chapters, list)
    assert len(work.chapters) > 0

@pytest.mark.api
@pytest.mark.asyncio
async def test_mangalib_live_fetch_first_chapter_contract(manga_url):
    client = MangalibClient()
    try:
        work = await client.inspect(manga_url)
        plan = FetchPlan(work=work, from_chapter=0, to_chapter=0)
        groups = await client.fetch(plan)
    finally:
        await client.close()

    assert len(groups) == 1
    assert groups[0].id >= 0
    assert len(groups[0].chunks) > 0