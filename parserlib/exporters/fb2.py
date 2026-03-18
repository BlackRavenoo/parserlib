from pathlib import Path

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ChunkGroup, WorkDescriptor

class Fb2Exporter(BaseExporter):
    name = "fb2"

    def _export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path,
    ) -> None:
        raise NotImplementedError("Fb2Exporter is not implemented yet")
