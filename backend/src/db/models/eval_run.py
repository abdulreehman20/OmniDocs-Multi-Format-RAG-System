from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EvalRun(SQLModel, table=True):
    __tablename__ = "eval_runs"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    dataset_version: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    chat_model_id: str | None = None
    eval_model_id: str | None = None
    prompt_version: str | None = None
    embedding_model_id: str | None = None
    retrieval_policy_version: str | None = None
    sample_count: int = 0
    aggregate_metrics: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    sample_results: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    correlation_id: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    finished_at: datetime | None = None
