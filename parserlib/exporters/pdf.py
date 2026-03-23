from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from PIL import Image

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ChunkGroup, ImageChunk, TextChunk
from parserlib.core.models import WorkDescriptor

PAGE_WIDTH_MM = 210
MAX_PAGE_HEIGHT_MM = 5000

class PdfExporter(BaseExporter):
    def _export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path,
    ) -> Path:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(0, 0, 0)
        pdf.set_font("Helvetica", size=12)

        first_page = True
        for group in groups:
            for chunk in group.chunks:
                if isinstance(chunk, ImageChunk):
                    self._place_image(pdf, chunk.payload)
                    first_page = False
                elif isinstance(chunk, TextChunk):
                    # TODO
                    if first_page:
                        pdf.add_page()
                        first_page = False
                    pdf.multi_cell(0, 8, chunk.text)
                    pdf.ln(4)

        target_path = Path(output_path) / f"{work.title}.pdf"
        pdf.output(str(target_path))
        return target_path

    def _place_image(self, pdf: FPDF, payload: bytes) -> None:
        with Image.open(BytesIO(payload)) as img:
            img_w_px, img_h_px = img.size
            img_format = img.format or "PNG"

            scale = PAGE_WIDTH_MM / img_w_px
            full_h_mm = img_h_px * scale

            if full_h_mm <= MAX_PAGE_HEIGHT_MM:
                pdf.add_page(format=(PAGE_WIDTH_MM, full_h_mm))
                pdf.image(BytesIO(payload), x=0, y=0, w=PAGE_WIDTH_MM, h=full_h_mm)
                return

            slice_h_px = int(MAX_PAGE_HEIGHT_MM / scale)

            y_offset = 0

            while y_offset < img_h_px:
                box = (0, y_offset, img_w_px, min(y_offset + slice_h_px, img_h_px))
                slice_img = img.crop(box)

                slice_h_mm = slice_img.height * scale

                buf = BytesIO()
                slice_img.save(buf, format=img_format)
                buf.seek(0)

                pdf.add_page(format=(PAGE_WIDTH_MM, slice_h_mm))
                pdf.image(buf, x=0, y=0, w=PAGE_WIDTH_MM, h=slice_h_mm)

                y_offset += slice_h_px