from typing import Type
from urllib.parse import urlparse

from parserlib.core.base_client import BaseClient

def _normalize_domain(domain: str) -> str:
    return domain.strip().lower().removeprefix("www.")

def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"URL has no domain: {url!r}")
    return parsed.netloc.removeprefix("www.").lower()

class ClientRegistry:
    _clients: dict[str, Type[BaseClient]] = {}

    @classmethod
    def register_client(cls, client_class: Type[BaseClient], domains: list[str]) -> None:
        for domain in domains:
            key = _normalize_domain(domain)
            cls._clients[key] = client_class

    @classmethod
    def get(cls, domain: str) -> Type[BaseClient]:
        key = _normalize_domain(domain)
        if key not in cls._clients:
            raise KeyError(f"No client registered for domain: {domain!r}")
        return cls._clients[key]
    
    @classmethod
    def get_by_url(cls, url: str) -> BaseClient:
        domain = _extract_domain(url)
        client_class = cls.get(domain)
        return client_class()

    @classmethod
    def all(cls) -> dict[str, Type[BaseClient]]:
        return dict(cls._clients)
