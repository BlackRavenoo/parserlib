from pathlib import Path
import re
from zipfile import ZipFile

from ebooklib import epub

from parserlib.core.base_exporter import BaseExporter
from parserlib.core.models import ChunkGroup, ImageChunk, TextChunk, WorkDescriptor

class EpubExporter(BaseExporter):
    supports_append = True

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
                uid=f"ch_{group.id}",
                title=group.title,
                file_name=f"chapter_{group.id}.xhtml",
                content=_get_chapter_content(group.title, parts).encode("utf-8")
            )

            book.add_item(chapter)
            spine.append(chapter)
            toc.append(epub.Link(chapter.file_name, group.title, f"ch_{group.id}"))

        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ["nav", *spine]

        target_path = Path(output_path) / f"{work.title}.epub"
        epub.write_epub(str(target_path), book, {"epub3_pages": False})
        return target_path

    @staticmethod
    def get_downloaded_chapter_ids(file_path: Path) -> set[int]:
        chapter_ids: set[int] = set()

        with ZipFile(file_path) as archive:
            for file_name in archive.namelist():
                match = re.search(r"(?:^|/)chapter_(\d+)\.xhtml$", file_name)
                if match:
                    chapter_ids.add(int(match.group(1)))

        return chapter_ids

    def append(
        self,
        work: WorkDescriptor,
        groups: list[ChunkGroup],
        file_path: Path,
    ) -> Path:
        book = epub.read_epub(str(file_path))
        existing_ids = self.get_downloaded_chapter_ids(file_path)

        groups_to_add = [group for group in groups if group.id not in existing_ids]
        if not groups_to_add:
            return file_path

        added_ids: set[int] = set()

        for group in groups_to_add:
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
                    parts.append(f'<img src="images/{img_id}.jpg"/>')

            chapter = epub.EpubHtml(
                uid=f"ch_{group.id}",
                title=group.title,
                file_name=f"chapter_{group.id}.xhtml",
                content=_get_chapter_content(group.title, parts).encode("utf-8"),
            )

            book.add_item(chapter)
            added_ids.add(group.id)

        all_ids = sorted(existing_ids | added_ids)
        chapter_title_by_id = {chapter.id: chapter.title for chapter in work.chapters}

        toc: list[epub.Link] = []
        spine: list[tuple[str, str]] = []

        for chapter_id in all_ids:
            href = f"chapter_{chapter_id}.xhtml"
            item = book.get_item_with_href(href)
            if item is None:
                continue

            item_id = item.get_id() or f"ch_{chapter_id}"
            title = chapter_title_by_id.get(chapter_id, f"Chapter {chapter_id}")

            toc.append(epub.Link(href, title, item_id))
            spine.append((item_id, "yes"))

        book.toc = toc
        book.spine = ["nav", *spine]

        epub.write_epub(str(file_path), book, {"epub3_pages": False})
        return file_path
    
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