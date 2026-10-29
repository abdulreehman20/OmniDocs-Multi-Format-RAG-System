from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


class IngestionJob(SQLModel, table=True):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (Index("ix_ingestion_jobs_status_created", "status", "created_at"),)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    generation: int = 1
    status: str = Field(default="queued", index=True)
    stage: str = Field(default="queued")
    attempts: int = 0
    inngest_event_id: str | None = Field(default=None, index=True)
    inngest_run_id: str | None = Field(default=None, index=True)
    correlation_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    cancelled: bool = False
    progress: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
