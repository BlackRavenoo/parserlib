from abc import ABC, abstractmethod
from dataclasses import replace
from pathlib import Path

from parserlib.core.models import ChunkGroup, WorkDescriptor
from parserlib.core.paths import sanitize_filename

class BaseExporter(ABC):
    supports_append: bool = False

    def export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path
    ) -> Path:
        safe_work = replace(work, title=sanitize_filename(work.title))
        return self._export(work=safe_work, groups=groups, output_path=output_path)

    def get_downloaded_chapter_ids(self, file_path: Path) -> set[int]:
        raise NotImplementedError("Append is not supported for this exporter")

    def append(self, work: WorkDescriptor, groups: list[ChunkGroup], file_path: Path) -> Path:
        raise NotImplementedError("Append is not supported for this exporter")

    @abstractmethod
    def _export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path
    ) -> Path:
        pass