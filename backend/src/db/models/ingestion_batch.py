from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class IngestionBatch(SQLModel, table=True):
    __tablename__ = "ingestion_batches"
    __table_args__ = (
        UniqueConstraint("job_id", "batch_number", name="uq_ingestion_batches_job_batch"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="ingestion_jobs.id", index=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    generation: int
    batch_number: int
    manifest_key: str | None = None
    status: str = Field(default="pending", index=True)
    retries: int = 0
    result: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
