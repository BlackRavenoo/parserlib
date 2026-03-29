import asyncio

from aiohttp import ClientError
from pyrate_limiter import Duration, Limiter, Rate
from pyrate_limiter.extras.aiohttp_limiter import RateLimitedSession

from parserlib.core.exceptions import RequestsBlockedByRateLimit

class HttpClient:
    def __init__(
        self,
        *,
        headers: dict[str, str],
        requests_per_minute: int = 90,
        retries: int = 3,
        retry_delay_seconds: float = 1.0,
        session: RateLimitedSession | None = None,
    ):
        self._session = session or RateLimitedSession(
            Limiter(
                Rate(
                    limit=requests_per_minute,
                    interval=Duration.MINUTE,
                ),
            ),
            headers=headers,
        )

        self._retries = retries
        self._retry_delay_seconds = retry_delay_seconds

    async def request_bytes(self, url: str) -> bytes:
        for attempt in range(self._retries + 1):
            try:
                response = await self._session.get(url)
            except (ClientError, TimeoutError):
                if attempt >= self._retries:
                    raise
                await asyncio.sleep(self._retry_delay_seconds * (attempt + 1))
                continue

            if response.status == 429:
                response.release()
                if attempt < self._retries:
                    await asyncio.sleep(self._retry_delay_seconds * (attempt + 1))
                    continue
                raise RequestsBlockedByRateLimit(
                    f"HTTP 429 received for URL: {url}. Retries exhausted."
                )

            if response.status >= 500:
                response.release()
                if attempt < self._retries:
                    await asyncio.sleep(self._retry_delay_seconds * (attempt + 1))
                    continue
                raise RuntimeError(f"Request failed with status {response.status}: {url}")

            if response.status >= 400:
                response.release()
                raise RuntimeError(f"Request failed with status {response.status}: {url}")

            return await response.read()

        raise RuntimeError(f"Request failed after retries: {url}")

    async def close(self) -> None:
        session = getattr(self._session, "_session", None)
        if session is not None and not session.closed:
            await session.close()
