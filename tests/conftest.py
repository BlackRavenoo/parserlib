import pytest

from parserlib.core.callback import ProgressCallback

class DummyCallback:
    def __call__(self, current: int, total: int, title: str) -> None:
        pass

@pytest.fixture
def callback() -> ProgressCallback:
    return DummyCallback()