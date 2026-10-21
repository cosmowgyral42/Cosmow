from pathlib import PurePath

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import split_text
from app.services.document_extraction import (
    ALLOWED_EXTENSIONS,
    MAX_DOCUMENT_BYTES,
    extract_text,
)


def create_document(
    db: Session,
    *,
    user_id: int,
    filename: str,
    content_type: str,
    content: bytes,
) -> Document:
    path = PurePath(filename)
    extension = path.suffix.lower()
    text = extract_text(filename, content)
    chunks = split_text(text)

    document = Document(
        user_id=user_id,
        title=path.stem.strip()[:255] or "Untitled",
        original_filename=path.name[:255],
        content_type="text/markdown" if extension == ".md" else "text/plain",
        file_size_bytes=len(content),
        status="uploaded",
    )

    try:
        db.add(document)
        db.flush()

        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    char_count=len(chunk),
                )
                for index, chunk in enumerate(chunks)
            ]
        )

        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise

    return document
