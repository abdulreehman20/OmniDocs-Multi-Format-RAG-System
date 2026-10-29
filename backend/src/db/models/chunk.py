from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_document_generation", "document_id", "generation"),
        UniqueConstraint("vector_id", name="uq_chunks_vector_id"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    generation: int
    vector_id: str = Field(index=True)
    chunk_index: int
    text: str | None = None
    text_sha256: str
    token_estimate: int = 0
    locator: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    chunker_version: str | None = None
    embedding_model_id: str | None = None
    state: str = Field(default="active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
