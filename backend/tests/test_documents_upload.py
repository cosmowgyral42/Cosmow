from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User

def register_and_login(client, email):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "TestPassword123",
            "timezone": "Asia/Kolkata",
        },
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPassword123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_upload_requires_authentication(client):
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 401


def test_upload_txt_succeeds(client, unique_email):
    headers = register_and_login(client, unique_email)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("notes.txt", b"Hello COSMOW", "text/plain")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "notes"
    assert data["file_size_bytes"] == len(b"Hello COSMOW")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == unique_email))
        document = db.get(Document, data["id"])
        assert user is not None
        assert document is not None
        assert document.user_id == user.id

        chunk = db.scalar(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )
        assert chunk is not None
        assert chunk.content == "Hello COSMOW"
        assert chunk.chunk_index == 0
    finally:
        db.close()


def test_upload_rejects_unsupported_extension(client, unique_email):
    headers = register_and_login(client, unique_email)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("payload.exe", b"not allowed", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_upload_rejects_empty_document(client, unique_email):
    headers = register_and_login(client, unique_email)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("empty.txt", b"   \n", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_invalid_utf8(client, unique_email):
    headers = register_and_login(client, unique_email)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("invalid.txt", b"\xff\xfe", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_file_over_one_mb(client, unique_email):
    headers = register_and_login(client, unique_email)
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("large.txt", b"x" * (1_048_577), "text/plain")},
    )
    assert response.status_code == 413
from sqlalchemy import select

from app.models.document_chunk import DocumentChunk


def test_upload_splits_long_document_into_chunks(client, unique_email):
    headers = register_and_login(client, unique_email)
    text = "a" * 2500

    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("long.txt", text.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    document_id = response.json()["id"]

    db = SessionLocal()
    try:
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()

        assert len(chunks) == 3
        assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
        assert all(chunk.char_count <= 1000 for chunk in chunks)
        assert chunks[0].content[-150:] == chunks[1].content[:150]
        assert chunks[1].content[-150:] == chunks[2].content[:150]
    finally:
        db.close()
