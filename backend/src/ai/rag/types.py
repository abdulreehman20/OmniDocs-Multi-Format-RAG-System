from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievedSource:
    label: str  # S1, S2, ...
    chunk_id: str
    vector_id: str
    document_id: str
    owner_id: str
    generation: int
    filename: str
    source_type: str | None
    locator: dict[str, Any]
    text: str
    score: float
    token_estimate: int = 0


@dataclass
class RetrievalResult:
    sources: list[RetrievedSource] = field(default_factory=list)
    filter_used: dict[str, Any] = field(default_factory=dict)
    candidate_count: int = 0
