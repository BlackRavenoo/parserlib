from typing import Protocol

class ProgressCallback(Protocol):
    def __call__(self, current: int, total: int, title: str) -> None:
        pass