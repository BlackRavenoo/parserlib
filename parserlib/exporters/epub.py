from pathlib import Path

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ChunkGroup, WorkDescriptor

class EpubExporter(BaseExporter):
    name = "epub"

    def _export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path,
    ) -> None:
        raise NotImplementedError("EpubExporter is not implemented yet")
