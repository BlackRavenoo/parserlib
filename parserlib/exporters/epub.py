from pathlib import Path

from ebooklib import epub

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ChunkGroup, ImageChunk, TextChunk, WorkDescriptor

class EpubExporter(BaseExporter):
    def _export(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        output_path: Path,
    ) -> Path:
        book = epub.EpubBook()
        book.set_title(work.title)

        spine = []
        toc = []

        for group in groups:
            parts = []

            for chunk in group.chunks:
                if isinstance(chunk, TextChunk):
                    parts.append(f"<p>{chunk.text}</p>")

                elif isinstance(chunk, ImageChunk):
                    img_id = f"img_{group.id}_{chunk.id}"
                    img_item = epub.EpubImage(
                        uid=img_id,
                        file_name=f"images/{img_id}.jpg",
                        media_type="image/jpeg",
                        content=chunk.payload,
                    )
                    book.add_item(img_item)
                    parts.append(
                        f'<img src="images/{img_id}.jpg"/>'
                    )

            chapter = epub.EpubHtml(
                title=group.title,
                file_name=f"chapter_{group.id}.xhtml",
                content=_get_chapter_content(group.title, parts).encode("utf-8")
            )

            book.add_item(chapter)
            spine.append(chapter)
            toc.append(epub.Link(chapter.file_name, group.title, f"ch_{group.id}"))

        book.toc = toc
        book.spine = spine

        for item in book.get_items():
            print(item.get_name(), len(item.get_content()))

        target_path = Path(output_path) / f"{work.title}.epub"
        epub.write_epub(str(target_path), book, {"epub3_pages": False})
        return target_path
    
def _get_chapter_content(title: str, parts: list[str]) -> str:
    return f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{title}</title>
  <style>
    body {{ margin: 0; padding: 1em; }}
    img  {{ display: block; width: 100%; height: auto; }}
    p    {{ line-height: 1.6; padding: 0 1em; }}
  </style>
</head>
<body>
  <h2>{title}</h2>
  {''.join(parts)}
</body>
</html>"""