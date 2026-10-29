from __future__ import annotations

import hashlib
import json
from typing import Any


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding_cache_key(
    *,
    model_id: str,
    preprocess_version: str,
    text: str,
) -> str:
    return f"emb:{model_id}:{preprocess_version}:{_sha256(text)}"


def retrieval_cache_key(
    *,
    owner_id: str,
    corpus_version: int,
    query: str,
    retrieval_version: str,
    scope: dict[str, Any],
) -> str:
    query_hash = _sha256(query.strip().lower())
    scope_hash = _sha256(json.dumps(scope, sort_keys=True, separators=(",", ":")))
    return (
        f"ret:{owner_id}:{corpus_version}:{query_hash}:{retrieval_version}:{scope_hash}"
    )


def scope_from_documents(documents: list[Any]) -> dict[str, Any]:
    """Stable selected-document scope for retrieval keys."""
    items = sorted(
        (
            {
                "id": d.id,
                "generation": d.active_generation,
            }
            for d in documents
        ),
        key=lambda x: x["id"],
    )
    return {"documents": items}
