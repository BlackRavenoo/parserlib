from aiohttp import ClientError
import pytest

from parserlib.core.exceptions import RequestsBlockedByRateLimit
from parserlib.core.http_client import HttpClient

class FakeResponse:
    def __init__(self, status: int, payload: bytes = b"ok"):
        self.status = status
        self._payload = payload
        self.released = False

    def release(self) -> None:
        self.released = True

    async def read(self) -> bytes:
        return self._payload

class FakeSession:
    def __init__(self, items: list[FakeResponse | Exception]):
        self._items = items
        self.calls = 0
        self.closed = False
        self._session = self

    async def get(self, _url: str):
        self.calls += 1
        item = self._items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def close(self):
        self.closed = True

@pytest.mark.asyncio
async def test_request_retries_on_server_errors_then_succeeds():
    session = FakeSession([
        FakeResponse(500),
        FakeResponse(502),
        FakeResponse(200, b"payload"),
    ])

    client = HttpClient(headers={}, retries=3, retry_delay_seconds=0, session=session)
    data = await client.request_bytes("https://example.com/resource")

    assert data == b"payload"
    assert session.calls == 3

@pytest.mark.asyncio
async def test_request_retries_on_429_then_succeeds():
    session = FakeSession([
        FakeResponse(429),
        FakeResponse(429),
        FakeResponse(200, b"ok"),
    ])

    client = HttpClient(headers={}, retries=3, retry_delay_seconds=0, session=session)
    data = await client.request_bytes("https://example.com/limited")

    assert data == b"ok"
    assert session.calls == 3

@pytest.mark.asyncio
async def test_request_does_not_block_after_429_retries_exhausted():
    session = FakeSession([
        FakeResponse(429),
        FakeResponse(429),
        FakeResponse(429),
        FakeResponse(200, b"unused"),
    ])

    client = HttpClient(headers={}, retries=2, retry_delay_seconds=0, session=session)

    with pytest.raises(RequestsBlockedByRateLimit):
        await client.request_bytes("https://example.com/limited")

    data = await client.request_bytes("https://example.com/second")

    assert data == b"unused"
    assert session.calls == 4

@pytest.mark.asyncio
async def test_request_retries_on_transport_errors_then_succeeds():
    session = FakeSession([
        ClientError("network"),
        FakeResponse(200, b"ok"),
    ])

    client = HttpClient(headers={}, retries=2, retry_delay_seconds=0, session=session)
    data = await client.request_bytes("https://example.com/retry")

    assert data == b"ok"
    assert session.calls == 2

@pytest.mark.asyncio
async def test_close_closes_underlying_session():
    session = FakeSession([FakeResponse(200, b"ok")])
    client = HttpClient(headers={}, retries=0, retry_delay_seconds=0, session=session)

    await client.close()

    assert session.closed is True
