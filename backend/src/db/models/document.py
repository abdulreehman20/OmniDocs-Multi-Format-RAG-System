from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class DocumentStatus(StrEnum):
    UPLOAD_PENDING = "upload_pending"
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class DocumentSourceType(StrEnum):
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    CSV = "csv"
    DOCX = "docx"


class Document(SQLModel, table=True):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_owner_status_updated", "owner_id", "status", "updated_at"),
        UniqueConstraint("object_bucket", "object_key", name="uq_documents_bucket_key"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    filename: str
    source_type: str
    mime_type: str
    byte_size: int = 0
    object_bucket: str
    object_key: str
    sha256: str | None = None
    status: str = Field(default=DocumentStatus.UPLOAD_PENDING, index=True)
    ingestion_stage: str | None = None
    ingestion_progress: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    active_generation: int = 0
    pending_generation: int | None = None
    chunk_count: int = 0
    parser_version: str | None = None
    chunker_version: str | None = None
    embedding_model_id: str | None = None
    source_config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    corpus_version: int = 0
    status_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None
