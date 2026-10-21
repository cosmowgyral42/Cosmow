import pytest

from app.services.chunking import split_text


def test_short_text_returns_one_chunk():
    assert split_text("hello") == ["hello"]


def test_long_text_respects_chunk_size():
    chunks = split_text("a" * 2500, chunk_size=1000, overlap=100)
    assert [len(chunk) for chunk in chunks] == [1000, 1000, 700]


def test_chunks_preserve_overlap():
    chunks = split_text("abcdefghij", chunk_size=6, overlap=2)
    assert chunks == ["abcdef", "efghij"]


def test_whitespace_only_returns_no_chunks():
    assert split_text("   \n ") == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (10, -1), (10, 10)],
)
def test_invalid_chunk_configuration(chunk_size, overlap):
    with pytest.raises(ValueError):
        split_text("hello world", chunk_size=chunk_size, overlap=overlap)
