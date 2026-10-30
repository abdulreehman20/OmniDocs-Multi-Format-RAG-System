from __future__ import annotations

import re
from typing import Any

from src.ai.rag.types import RetrievedSource

_CITATION_RE = re.compile(r"\[(S\d+)\]")


def extract_citation_labels(text: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _CITATION_RE.finditer(text or ""):
        label = match.group(1)
        if label not in seen:
            seen.add(label)
            ordered.append(label)
    return ordered


def validate_citations(
    answer: str,
    sources: list[RetrievedSource],
) -> list[RetrievedSource]:
    """Keep only citation labels that exist in the retrieved set."""
    allowed = {s.label: s for s in sources}
    return [allowed[label] for label in extract_citation_labels(answer) if label in allowed]


def citation_record_payload(source: RetrievedSource) -> dict[str, Any]:
    excerpt = (source.text or "")[:280]
    return {
        "label": source.label,
        "document_id": source.document_id,
        "chunk_id": source.chunk_id,
        "generation": source.generation,
        "filename": source.filename,
        "source_type": source.source_type,
        "locator": dict(source.locator or {}),
        "excerpt": excerpt or None,
    }
