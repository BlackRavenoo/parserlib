from io import BytesIO
from pathlib import Path

from fpdf import FPDF

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ImageChunk, TextChunk

class PdfExporter(BaseExporter):
    name = "pdf"

    def _export(self, work, groups, output_path):
        pdf = FPDF()

        pdf.set_font("Arial", size=12)

        for group in groups:
            pdf.add_page()
            for chunk in group.chunks:
                if isinstance(chunk, TextChunk):
                    pdf.multi_cell(0, 8, chunk.text)
                    pdf.ln(4)
                elif isinstance(chunk, ImageChunk):
                    pdf.image(BytesIO(chunk.payload), w=pdf.epw)

        target_path = Path(output_path) / f"{work.title}.pdf"
        pdf.output(str(target_path))