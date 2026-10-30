from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


class MessageCitation(SQLModel, table=True):
    __tablename__ = "message_citations"
    __table_args__ = (Index("ix_message_citations_message", "message_id"),)

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    message_id: str = Field(foreign_key="messages.id", index=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    chunk_id: str | None = Field(default=None, foreign_key="chunks.id")
    label: str  # S1, S2, ...
    generation: int
    filename: str
    source_type: str | None = None
    locator: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    excerpt: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
