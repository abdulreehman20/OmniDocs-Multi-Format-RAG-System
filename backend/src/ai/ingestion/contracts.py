from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedUnit:
    text: str
    locator: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDocument:
    units: list[ExtractedUnit]
    parser_version: str
    warnings: list[str] = field(default_factory=list)
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkUnit:
    chunk_index: int
    text: str
    text_sha256: str
    token_estimate: int
    locator: dict[str, Any]
    chunker_version: str
    embedding_model_id: str
    generation: int

    @property
    def chunk_id(self) -> str:
        return f"c{self.chunk_index}"
