import pytest

from parserlib.core.client_loader import load_clients
from parserlib.core.models import FetchPlan
from parserlib.core.registry import ClientRegistry

@pytest.fixture(scope="session", autouse=True)
def init_clients():
    load_clients()

@pytest.mark.asyncio
@pytest.mark.api
@pytest.mark.parametrize(
    "url",
    [
        pytest.param(
            "https://mangalib.me/ru/manga/1064--kono-subarashii-sekai-ni-shukufuku-o",
            id="mangalib.me",
        ),
        pytest.param(
            "https://mangalib.org/ru/manga/1064--kono-subarashii-sekai-ni-shukufuku-o",
            id="mangalib.org",
        ),
        pytest.param(
            "https://ranobelib.me/ru/book/12021--kono-subarashii-sekai-ni-shukufuku-wo",
            id="ranobelib.me"
        )
    ]
)
async def test_live_full_fetching_pipeline(url, callback):
    client = ClientRegistry.get_by_url(url)
    try:
        work = await client.inspect(url)

        assert work.slug
        assert work.title
        assert work.source_url == url
        assert isinstance(work.chapters, list)
        assert len(work.chapters) > 0

        plan = FetchPlan(work=work, from_chapter=0, to_chapter=0)
        groups = await client.fetch(plan, callback)

        assert len(groups) == 1
        assert groups[0].id >= 0
        assert len(groups[0].chunks) > 0
    finally:
        await client.close()