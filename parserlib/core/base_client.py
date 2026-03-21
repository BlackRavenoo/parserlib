from abc import ABC, abstractmethod
from typing import Union

from parserlib.core.callback import ProgressCallback
from parserlib.core.models import ChunkGroup, FetchPlan, WorkDescriptor

class BaseClient(ABC):
    name: str
    base_url: Union[str, list[str]]

    @abstractmethod
    async def inspect(self, url: str) -> WorkDescriptor:
        pass

    @abstractmethod
    async def _fetch(self, plan: FetchPlan, progress_callback: ProgressCallback) -> list[ChunkGroup]:
        pass

    async def fetch(self, plan: FetchPlan, progress_callback: ProgressCallback) -> list[ChunkGroup]:
        groups = await self._fetch(plan, progress_callback)
        
        groups.sort(key=lambda group: group.id)
        
        return groups

    # Override if needed
    async def close(self) -> None:
        pass

    async def __aenter__(self) -> "BaseClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
