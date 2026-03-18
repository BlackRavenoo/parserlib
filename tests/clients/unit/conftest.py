import pytest
import pytest_asyncio
from msgspec.json import encode
from unittest.mock import AsyncMock

from parserlib.clients.mangalib.client import MangalibClient

@pytest.fixture(scope="session")
def mangalib_slug() -> str:
    return "1--test-manga"

@pytest.fixture(scope="session")
def mangalib_url(mangalib_slug: str) -> str:
    return f"https://mangalib.me/ru/manga/{mangalib_slug}"

@pytest.fixture(scope="session")
def mangalib_mock_responses(mangalib_slug: str) -> dict[str, bytes]:
    api_url = "https://api.cdnlibs.org/api/manga"
    image_url = "https://img3.mixlib.me"

    manga_payload = {
        "data": {
            "id": 1,
            "name": "test-manga",
            "rus_name": "Тестовая манга",
            "cover": {"filename": "cover.jpg"},
        }
    }

    chapters_payload = {
        "data": [
            {
                "id": 101,
                "index": 1,
                "item_number": 1,
                "volume": "1",
                "number": "1",
                "number_secondary": "",
                "name": "Старт",
                "branches": [
                    {
                        "id": 1,
                        "branch_id": None,
                        "teams": [{"id": 11, "name": "Team A"}],
                    }
                ],
            },
            {
                "id": 102,
                "index": 2,
                "item_number": 2,
                "volume": "1",
                "number": "2",
                "number_secondary": "",
                "name": "Продолжение",
                "branches": [
                    {
                        "id": 2,
                        "branch_id": None,
                        "teams": [{"id": 12, "name": "Team B"}],
                    }
                ],
            },
        ]
    }

    chapter_one_payload = {
        "data": {
            "id": 101,
            "volume": "1",
            "number": "1",
            "number_secondary": "",
            "name": "Старт",
            "teams": [{"id": 11, "name": "Team A"}],
            "pages": [
                {"id": 1, "url": "/images/ch1-p1.jpg"},
                {"id": 2, "url": "/images/ch1-p2.jpg"},
            ],
        }
    }

    return {
        f"{api_url}/{mangalib_slug}?fields[]=teams": encode(manga_payload),
        f"{api_url}/{mangalib_slug}/chapters": encode(chapters_payload),
        f"{api_url}/{mangalib_slug}/chapter?number=1&volume=1": encode(chapter_one_payload),
        f"{image_url}/images/ch1-p1.jpg": b"image-bytes-1",
        f"{image_url}/images/ch1-p2.jpg": b"image-bytes-2",
    }

@pytest_asyncio.fixture
async def mangalib_client(mangalib_mock_responses: dict[str, bytes]) -> MangalibClient: # type: ignore
    client = MangalibClient()

    async def fake_request_bytes(url: str) -> bytes:
        try:
            return mangalib_mock_responses[url]
        except KeyError as exc:
            raise AssertionError(f"Unexpected request URL in test: {url}") from exc

    client._request_bytes = AsyncMock(side_effect=fake_request_bytes)

    try:
        yield client
    finally:
        await client.close()