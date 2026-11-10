from datetime import datetime
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_db
from app.models.document import Document
from app.models.user import User
from app.services.document_service import (
    ALLOWED_EXTENSIONS,
    MAX_DOCUMENT_BYTES,
    create_document,
)
from app.services.document_embedding_service import (
    DocumentEmbeddingError,
    embed_document,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    created_at: datetime


class EmbeddingResponse(BaseModel):
    document_id: int
    chunks_embedded: int
    status: str


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.scalars(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    ).all()


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    filename = file.filename or ""

    if PurePath(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Only .txt and .md files are supported.",
        )

    try:
        content = await file.read(MAX_DOCUMENT_BYTES + 1)
    finally:
        await file.close()

    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 1 MB limit.",
        )

    try:
        return create_document(
            db,
            user_id=current_user.id,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/{document_id}/embed", response_model=EmbeddingResponse)
def embed_uploaded_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        count = embed_document(
            db,
            user_id=current_user.id,
            document_id=document_id,
        )
    except LookupError:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        ) from None
    except DocumentEmbeddingError:
        raise HTTPException(
            status_code=503,
            detail="Document embedding is temporarily unavailable.",
        ) from None

    return EmbeddingResponse(
        document_id=document_id,
        chunks_embedded=count,
        status="indexed",
    )

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    db.delete(document)
    db.commit()

