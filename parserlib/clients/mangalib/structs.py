from msgspec.structs import Struct

from parserlib.core.models import ChapterEntry

# Manga metadata

class Cover(Struct):
    filename: str

class MangaData(Struct):
    id: int
    name: str
    rus_name: str
    cover: Cover

class Manga(Struct):
    data: MangaData

# Manga chapters data

class Team(Struct):
    id: int
    name: str

class Branch(Struct):
    id: int
    branch_id: None | int
    teams: list[Team]

class Chapter(Struct):
    id: int
    index: int
    item_number: int
    volume: str
    number: str
    number_secondary: str
    name: str | None
    branches: list[Branch]

    def into_core(self) -> ChapterEntry:
        title = f"Том {self.volume}, Глава {self.number}"
        
        if self.name:
            title += f" - {self.name}"
        
        return ChapterEntry(
            id=self.index,
            title=title,
            key=f"number={self.number}&volume={self.volume}"
        )
    
    def __post_init__(self):
        if self.name is None:
            self.name = ""

class MangaChapters(Struct):
    data: list[Chapter]

# Chapter data

class Page(Struct):
    id: int
    url: str

class ChapterData(Struct):
    id: int
    volume: str
    number: str
    number_secondary: str
    name: str | None
    teams: list[Team]
    pages: list[Page]

class MangaChapter(Struct):
    data: ChapterData