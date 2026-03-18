from enum import StrEnum
from typing import Type

from parserlib.core.base_exporter import BaseExporter
from parserlib.exporters.epub import EpubExporter
from parserlib.exporters.fb2 import Fb2Exporter
from parserlib.exporters.pdf import PdfExporter

class ExporterKind(StrEnum):
    PDF = "pdf"
    EPUB = "epub"
    FB2 = "fb2"

EXPORTERS: dict[ExporterKind, Type[BaseExporter]] = {
    ExporterKind.PDF: PdfExporter,
    ExporterKind.EPUB: EpubExporter,
    ExporterKind.FB2: Fb2Exporter,
}
def list_exporter_names() -> list[str]:
    return [kind.value for kind in ExporterKind]

def create_exporter(kind: ExporterKind) -> BaseExporter:
    return EXPORTERS[kind]()
