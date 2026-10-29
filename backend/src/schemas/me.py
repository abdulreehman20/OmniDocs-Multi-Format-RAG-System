from typing import Any

from pydantic import BaseModel, Field


class MeResponse(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    corpus_version: int = 0
    created_at: str
    updated_at: str


class MeUpdate(BaseModel):
    display_name: str | None = None
    preferences: dict[str, Any] | None = None
