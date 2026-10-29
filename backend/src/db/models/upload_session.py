from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


class UploadSession(SQLModel, table=True):
    __tablename__ = "upload_sessions"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    expected_size: int
    mime_type: str
    object_key: str
    expires_at: datetime
    completed: bool = False
    uploaded_size: int | None = None
    etag: str | None = None
    client_checksum: str | None = None
    idempotency_key: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
