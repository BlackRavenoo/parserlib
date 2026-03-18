from dataclasses import dataclass

@dataclass
class ChapterEntry:
    id: int
    title: str
    key: str

@dataclass
class WorkDescriptor:
    title: str
    slug: str
    source_url: str
    chapters: list[ChapterEntry]

@dataclass
class FetchPlan:
    work: WorkDescriptor
    from_chapter: int
    to_chapter: int

@dataclass
class DataChunk:
    id: int

@dataclass
class TextChunk(DataChunk):
    text: str

@dataclass
class ImageChunk(DataChunk):
    payload: bytes

@dataclass
class ChunkGroup:
    id: int
    chunks: list[DataChunk]