from base64 import b64encode
from pathlib import Path
from xml.etree import ElementTree

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ChunkGroup, ImageChunk, TextChunk, WorkDescriptor

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"
XLINK_NS = "http://www.w3.org/1999/xlink"

class Fb2Exporter(BaseExporter):
    supports_append = False

    def _export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path,
    ) -> Path:
        ElementTree.register_namespace("", FB2_NS)
        ElementTree.register_namespace("xlink", XLINK_NS)

        fb2 = ElementTree.Element(f"{{{FB2_NS}}}FictionBook")

        desc = ElementTree.SubElement(fb2, "description")
        title_info = ElementTree.SubElement(desc, "title-info")
        book_title = ElementTree.SubElement(title_info, "book-title")
        book_title.text = work.title

        body = ElementTree.SubElement(fb2, "body")

        image_ids = []

        for group in groups:
            section = ElementTree.SubElement(body, "section")
            title_el = ElementTree.SubElement(section, "title")
            title_p = ElementTree.SubElement(title_el, "p")
            title_p.text = group.title

            for chunk in group.chunks:
                if isinstance(chunk, TextChunk):
                    p = ElementTree.SubElement(section, "p")
                    p.text = chunk.text

                elif isinstance(chunk, ImageChunk):
                    img_id = f"img_{group.id}_{chunk.id}"
                    image_ids.append((img_id, chunk.payload))

                    img_el = ElementTree.SubElement(section, "image")
                    img_el.set(f"{{{XLINK_NS}}}href", f"#{img_id}")

        for img_id, payload in image_ids:
            binary = ElementTree.SubElement(fb2, "binary")
            binary.set("id", img_id)
            binary.set("content-type", "image/jpeg")
            binary.text = b64encode(payload).decode("ascii")

        path = Path(output_path) / f"{work.title}.fb2"
        tree = ElementTree.ElementTree(fb2)
        ElementTree.indent(tree)
        tree.write(str(path), encoding="utf-8", xml_declaration=True)
        return path