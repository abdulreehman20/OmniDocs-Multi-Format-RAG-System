from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class OutboxEvent(SQLModel, table=True):
    __tablename__ = "outbox_events"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    event_name: str
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    dispatch_state: str = Field(default="pending", index=True)
    attempts: int = 0
    next_retry_at: datetime | None = None
    inngest_event_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dispatched_at: datetime | None = None
