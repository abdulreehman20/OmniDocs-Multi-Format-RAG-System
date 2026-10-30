from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class PromptVersion(SQLModel, table=True):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("prompt_key", "version", name="uq_prompt_versions_key_version"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    prompt_key: str = Field(index=True)
    version: int
    template: str
    template_sha256: str
    model_id: str | None = None
    retrieval_policy_version: str = "baseline-v1"
    status: str = Field(default="active", index=True)  # draft|canary|active|retired
    changelog: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
