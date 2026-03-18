import pytest

from parserlib.core.paths import sanitize_filename

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Vigilante: Boku no Hero Academia Illegals", "Vigilante_ Boku no Hero Academia Illegals"),
        ("  valid name  ", "  valid name  "),
    ],
)
def test_sanitize_filename(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected