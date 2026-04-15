import base64
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from PIL import Image
import pytest

from parserlib.core.exporters import ExporterKind, create_exporter
from parserlib.core.models import ChunkGroup, ImageChunk, TextChunk, WorkDescriptor
from parserlib.exporters.epub import EpubExporter
from parserlib.exporters.fb2 import XLINK_NS

def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

@pytest.fixture
def make_work():
    def _factory(title: str) -> WorkDescriptor:
        return WorkDescriptor(
            title=title,
            slug="test-123",
            source_url="https://something.com",
            chapters=[],
        )
    return _factory

@pytest.fixture(scope="function")
def payload() -> bytes:
    img = Image.new("RGB", (16, 16), color=(255, 255, 255))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()

@pytest.fixture
def groups(payload):
    return [
        ChunkGroup(
            id=1,
            title="Chapter 1",
            chunks=[TextChunk(id=1, text="chapter text"), ImageChunk(id=2, payload=payload)],
        )
    ]

def test_exporter_creates_file_with_sanitized_name(
    exporter,
    tmp_path,
    groups,
    make_work
):
    work = make_work("Test\\/:*?\"<>|Title")

    result = exporter.export(work=work, groups=groups, output_path=tmp_path)

    assert result.exists()
    assert result.name.startswith("Test_________Title")

def test_fb2_export_contains_text_and_image(
    tmp_path,
    groups,
    make_work,
    payload
):
    exporter = create_exporter(ExporterKind.FB2)

    result = exporter.export(
        work=make_work("FB2 book"),
        groups=groups,
        output_path=tmp_path,
    )

    root = ElementTree.parse(result).getroot()
    elements = list(root.iter())

    p_texts = [el.text for el in elements if _local_name(el.tag) == "p" and el.text]
    assert "chapter text" in p_texts

    images = [el for el in elements if _local_name(el.tag) == "image"]
    assert len(images) == 1
    assert images[0].attrib[f"{{{XLINK_NS}}}href"] == "#img_1_2"

    binaries = [el for el in elements if _local_name(el.tag) == "binary"]
    assert len(binaries) == 1
    assert binaries[0].attrib["id"] == "img_1_2"
    assert binaries[0].text == base64.b64encode(payload).decode("ascii")

def test_epub_export_contains_text_and_image(
    tmp_path,
    groups,
    make_work,
    payload
):
    exporter = create_exporter(ExporterKind.EPUB)

    result = exporter.export(
        work=make_work("EPUB book"),
        groups=groups,
        output_path=tmp_path,
    )

    with ZipFile(result) as archive:
        names = archive.namelist()
        chapter_name = next(name for name in names if name.endswith("chapter_1.xhtml"))
        image_name = next(name for name in names if name.endswith("images/img_1_2.jpg"))

        chapter_content = archive.read(chapter_name).decode("utf-8")
        image_content = archive.read(image_name)

    assert "<h2>Chapter 1</h2>" in chapter_content
    assert "<p>chapter text</p>" in chapter_content
    assert image_content == payload

def test_pdf_export_creates_valid_pdf_header(
    tmp_path,
    groups,
    make_work,
    payload
):
    exporter = create_exporter(ExporterKind.PDF)

    result = exporter.export(
        work=make_work("PDF book"),
        groups=groups,
        output_path=tmp_path,
    )

    content = result.read_bytes()
    assert content.startswith(b"%PDF")
    assert len(content) > 200

def test_epub_append_adds_only_missing_chapters(
    tmp_path,
    make_work,
    payload,
):
    exporter = EpubExporter()
    work = make_work("EPUB append")

    initial_groups = [
        ChunkGroup(
            id=1,
            title="Chapter 1",
            chunks=[TextChunk(id=1, text="chapter 1 text"), ImageChunk(id=2, payload=payload)],
        )
    ]
    file_path = exporter.export(work=work, groups=initial_groups, output_path=tmp_path)

    assert exporter.get_downloaded_chapter_ids(file_path) == {1}

    groups_to_append = [
        ChunkGroup(
            id=1,
            title="Chapter 1 duplicate",
            chunks=[TextChunk(id=1, text="should not be appended")],
        ),
        ChunkGroup(
            id=2,
            title="Chapter 2",
            chunks=[TextChunk(id=1, text="chapter 2 text")],
        ),
    ]

    exporter.append(work=work, groups=groups_to_append, file_path=file_path)

    with ZipFile(file_path) as archive:
        names = archive.namelist()
        chapter_1 = [name for name in names if name.endswith("chapter_1.xhtml")]
        chapter_2 = [name for name in names if name.endswith("chapter_2.xhtml")]

        chapter_1_content = archive.read(chapter_1[0]).decode("utf-8")
        chapter_2_content = archive.read(chapter_2[0]).decode("utf-8")

    assert len(chapter_1) == 1
    assert len(chapter_2) == 1
    assert "chapter 1 text" in chapter_1_content
    assert "should not be appended" not in chapter_1_content
    assert "chapter 2 text" in chapter_2_content