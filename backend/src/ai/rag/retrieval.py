from __future__ import annotations

import math
from typing import Any

from sqlmodel import Session, col, select

from src.ai.rag.types import RetrievedSource, RetrievalResult
from src.config import Settings
from src.db.models import Chunk, Document, DocumentStatus
from src.db.redis import cache_from_settings
from src.providers.cache_keys import retrieval_cache_key, scope_from_documents
from src.providers.protocols import Cache, EmbeddingProvider, VectorMatch, VectorStore
from src.services.corpus import get_user_corpus_version


def _cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _mmr_select(
    candidates: list[tuple[RetrievedSource, list[float]]],
    *,
    query_vector: list[float],
    k: int,
    lambda_mult: float = 0.7,
) -> list[RetrievedSource]:
    if not candidates or k <= 0:
        return []
    remaining = list(candidates)
    selected: list[tuple[RetrievedSource, list[float]]] = []
    while remaining and len(selected) < k:
        best_i = 0
        best_score = float("-inf")
        for i, (src, vec) in enumerate(remaining):
            relevance = _cosine(query_vector, vec)
            diversity = 0.0
            if selected:
                diversity = max(_cosine(vec, svec) for _, svec in selected)
            mmr = lambda_mult * relevance - (1 - lambda_mult) * diversity
            # Prefer higher retrieval score as a soft tie-break.
            mmr += 0.01 * src.score
            if mmr > best_score:
                best_score = mmr
                best_i = i
        selected.append(remaining.pop(best_i))
    return [s for s, _ in selected]


def build_pinecone_filter(
    *,
    owner_id: str,
    documents: list[Document],
) -> dict[str, Any]:
    """Server-derived filter: owner + selected docs + each doc's active generation."""
    doc_ids = [d.id for d in documents]
    generations = sorted({d.active_generation for d in documents})
    filt: dict[str, Any] = {
        "owner_id": {"$eq": owner_id},
        "document_id": {"$in": doc_ids},
    }
    if len(generations) == 1:
        filt["generation"] = {"$eq": generations[0]}
    else:
        filt["generation"] = {"$in": generations}
    return filt


def retrieve_for_chat(
    session: Session,
    *,
    settings: Settings,
    embeddings: EmbeddingProvider,
    vectors: VectorStore,
    owner_id: str,
    documents: list[Document],
    query: str,
    cache: Cache | None = None,
) -> RetrievalResult:
    if not documents:
        return RetrievalResult()

    for doc in documents:
        if doc.owner_id != owner_id or doc.status != DocumentStatus.READY:
            raise PermissionError("document not ready or not owned")

    query_vector = embeddings.embed_query(query)
    filt = build_pinecone_filter(owner_id=owner_id, documents=documents)
    corpus_version = get_user_corpus_version(session, owner_id)
    scope = scope_from_documents(documents)
    cache_client = cache if cache is not None else cache_from_settings(settings)
    ret_key = retrieval_cache_key(
        owner_id=owner_id,
        corpus_version=corpus_version,
        query=query,
        retrieval_version=settings.retrieval_policy_version,
        scope=scope,
    )
    matches: list[VectorMatch] = []
    cached = cache_client.get_json(ret_key)
    if isinstance(cached, list):
        for item in cached:
            if not isinstance(item, dict) or "id" not in item:
                continue
            matches.append(
                {
                    "id": str(item["id"]),
                    "score": float(item.get("score") or 0.0),
                    "metadata": dict(item.get("metadata") or {}),
                }
            )
    else:
        matches = vectors.query(
            namespace=owner_id,
            vector=query_vector,
            top_k=settings.max_retrieval_candidates,
            filter=filt,
        )
        # Cache ids/scores/metadata only — hydrate text from Postgres.
        cache_client.set_json(
            ret_key,
            [
                {
                    "id": m["id"],
                    "score": m["score"],
                    "metadata": m.get("metadata") or {},
                }
                for m in matches
            ],
            ttl_seconds=settings.retrieval_cache_ttl_seconds,
        )

    if not matches:
        return RetrievalResult(filter_used=filt, candidate_count=0)

    vector_ids = [m["id"] for m in matches]
    score_by_vid = {m["id"]: m["score"] for m in matches}
    meta_by_vid = {m["id"]: m["metadata"] for m in matches}

    chunks = list(
        session.exec(
            select(Chunk).where(
                Chunk.owner_id == owner_id,
                col(Chunk.vector_id).in_(vector_ids),
                Chunk.state == "active",
            )
        ).all()
    )
    chunk_by_vid = {c.vector_id: c for c in chunks}
    doc_by_id = {d.id: d for d in documents}

    hydrated: list[tuple[RetrievedSource, list[float]]] = []
    seen_chunk_ids: set[str] = set()
    for vid in vector_ids:
        chunk = chunk_by_vid.get(vid)
        if chunk is None or chunk.id in seen_chunk_ids:
            continue
        doc = doc_by_id.get(chunk.document_id)
        if doc is None:
            continue
        # Reject stale generations relative to the document's active generation.
        if chunk.generation != doc.active_generation:
            continue
        seen_chunk_ids.add(chunk.id)
        meta = meta_by_vid.get(vid, {})
        # Fake store keeps values; Pinecone query doesn't return vectors — use score only.
        stored = None
        if hasattr(vectors, "vectors"):
            bucket = getattr(vectors, "vectors", {}).get(owner_id, {})
            rec = bucket.get(vid)
            if rec:
                stored = rec.get("values")
        vec = stored if isinstance(stored, list) else query_vector
        source = RetrievedSource(
            label="",  # assigned after selection
            chunk_id=chunk.id,
            vector_id=vid,
            document_id=chunk.document_id,
            owner_id=chunk.owner_id,
            generation=chunk.generation,
            filename=doc.filename,
            source_type=doc.source_type,
            locator=dict(chunk.locator or meta.get("locator") or {}),
            text=chunk.text or "",
            score=float(score_by_vid.get(vid, 0.0)),
            token_estimate=chunk.token_estimate or max(1, len(chunk.text or "") // 4),
        )
        hydrated.append((source, vec))

    selected = _mmr_select(
        hydrated,
        query_vector=query_vector,
        k=settings.max_context_chunks,
    )

    # Enforce rough token budget.
    budgeted: list[RetrievedSource] = []
    tokens = 0
    for src in selected:
        if tokens + src.token_estimate > settings.max_context_tokens and budgeted:
            break
        budgeted.append(src)
        tokens += src.token_estimate

    for i, src in enumerate(budgeted, start=1):
        src.label = f"S{i}"

    return RetrievalResult(
        sources=budgeted,
        filter_used=filt,
        candidate_count=len(matches),
    )
