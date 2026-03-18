import pytest

from parserlib.core.models import FetchPlan, ImageChunk

@pytest.mark.asyncio
async def test_mangalib_client_inspect(mangalib_client, mangalib_url):
    work = await mangalib_client.inspect(mangalib_url)

    assert work.slug == "1--test-manga"
    assert work.title == "Тестовая манга"
    assert len(work.chapters) == 2

@pytest.mark.asyncio
async def test_mangalib_client_fetch_one_chapter(mangalib_client, mangalib_url):
    work = await mangalib_client.inspect(mangalib_url)
    plan = FetchPlan(work=work, from_chapter=0, to_chapter=0)

    groups = await mangalib_client.fetch(plan)

    assert len(groups) == 1
    assert groups[0].id == 1
    assert len(groups[0].chunks) == 2
    assert all(isinstance(chunk, ImageChunk) for chunk in groups[0].chunks)
    assert groups[0].chunks[0].payload == b"image-bytes-1"