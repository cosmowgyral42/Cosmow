import pytest

from app.services.document_extraction import (
    MAX_DOCUMENT_BYTES,
    MAX_EXTRACTED_CHARACTERS,
    extract_text,
)


def test_extracts_plain_text():
    assert extract_text("notes.txt", b"Hello COSMOW") == "Hello COSMOW"


def test_extracts_markdown_and_removes_utf8_bom():
    assert extract_text("notes.md", b"\xef\xbb\xbf# COSMOW") == "# COSMOW"


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("notes.exe", b"text"),
        ("empty.txt", b""),
        ("empty.md", b"  \n "),
        ("invalid.txt", b"\xff\xfe"),
    ],
)
def test_rejects_invalid_documents(filename, content):
    with pytest.raises(ValueError):
        extract_text(filename, content)


def test_rejects_file_over_one_mb():
    with pytest.raises(ValueError, match="1 MB"):
        extract_text("large.txt", b"x" * (MAX_DOCUMENT_BYTES + 1))


def test_character_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_extraction.MAX_EXTRACTED_CHARACTERS", 3
    )
    with pytest.raises(ValueError, match="character limit"):
        extract_text("notes.txt", b"four")
