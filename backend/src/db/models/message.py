from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, Index, UniqueConstraint
from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        UniqueConstraint(
            "conversation_id",
            "idempotency_key",
            name="uq_messages_conversation_idempotency",
        ),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", index=True)
    owner_id: str = Field(foreign_key="users.id", index=True)
    role: str  # user | assistant | system
    content: str = ""
    status: str = Field(default="completed")  # streaming|completed|partial|failed
    idempotency_key: str | None = Field(default=None, index=True)
    prompt_version_id: str | None = None
    model_id: str | None = None
    embedding_model_id: str | None = None
    retrieval_config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    corpus_version: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
