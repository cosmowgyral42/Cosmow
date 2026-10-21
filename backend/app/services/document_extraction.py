from pathlib import PurePath

MAX_DOCUMENT_BYTES = 1_048_576
MAX_EXTRACTED_CHARACTERS = 1_000_000
ALLOWED_EXTENSIONS = {".txt", ".md"}


def extract_text(filename: str, content: bytes) -> str:
    """Extract bounded UTF-8 text from a TXT or Markdown document."""
    extension = PurePath(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .txt and .md files are supported.")

    if not content or len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("File must be between 1 byte and 1 MB.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("File must contain valid UTF-8 text.") from None

    if len(text) > MAX_EXTRACTED_CHARACTERS:
        raise ValueError("Extracted text exceeds the character limit.")

    if not text.strip():
        raise ValueError("Document is empty.")

    return text
