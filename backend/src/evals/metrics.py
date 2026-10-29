from __future__ import annotations

import re

from src.ai.rag.citations import extract_citation_labels, validate_citations
from src.ai.rag.types import RetrievedSource

_ABSTAIN_RE = re.compile(
    r"couldn'?t find enough information|not enough (information|evidence)|"
    r"do not have enough|insufficient (information|evidence)",
    re.IGNORECASE,
)


def citation_validity_score(answer: str, sources: list[RetrievedSource]) -> float:
    labels = extract_citation_labels(answer)
    if not labels:
        return 1.0 if not sources else 0.5
    valid = validate_citations(answer, sources)
    return len(valid) / len(labels)


def abstention_quality(
    *,
    answerable: bool,
    answer: str,
) -> float:
    abstained = bool(_ABSTAIN_RE.search(answer or ""))
    if not answerable:
        return 1.0 if abstained else 0.0
    return 0.0 if abstained and len((answer or "").strip()) < 80 else 1.0


def aggregate_custom_metrics(rows: list[dict]) -> dict[str, float]:
    if not rows:
        return {
            "citation_validity": 0.0,
            "abstention_quality": 0.0,
        }
    return {
        "citation_validity": sum(r["citation_validity"] for r in rows) / len(rows),
        "abstention_quality": sum(r["abstention_quality"] for r in rows) / len(rows),
    }
