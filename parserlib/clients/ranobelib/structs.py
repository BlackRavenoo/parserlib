from msgspec import Struct

from parserlib.clients.mangalib.structs import Team

class ChapterData(Struct):
    id: int
    volume: str
    number: str
    number_secondary: str
    name: str | None
    teams: list[Team]
    content: str | dict

class RanobeChapter(Struct):
    data: ChapterData