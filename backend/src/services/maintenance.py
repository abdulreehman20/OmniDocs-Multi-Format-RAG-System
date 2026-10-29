from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, col, select

from src.config import Settings
from src.db.models import Chunk, Document, DocumentStatus, UploadSession
from src.providers.protocols import ObjectStorage, VectorStore


def dispatch_pending_outbox(session: Session, *, limit: int = 50) -> dict[str, int]:
    from src.services import ingestion as ingestion_service
    from src.services.outbox import try_dispatch_outbox

    events = ingestion_service.pending_outbox_events(session, limit=limit)
    dispatched = 0
    for event in events:
        try_dispatch_outbox(session, event)
        session.refresh(event)
        if event.dispatch_state == "dispatched":
            dispatched += 1
    return {"pending_seen": len(events), "dispatched": dispatched}


def cleanup_abandoned_uploads(
    session: Session,
    storage: ObjectStorage,
    settings: Settings,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.abandoned_upload_ttl_seconds)
    rows = list(
        session.exec(
            select(UploadSession)
            .where(
                UploadSession.completed == False,  # noqa: E712
                UploadSession.expires_at < now,
            )
            .limit(settings.maintenance_batch_size)
        ).all()
    )
    # Also catch very old incomplete sessions past TTL from created_at.
    older = list(
        session.exec(
            select(UploadSession)
            .where(
                UploadSession.completed == False,  # noqa: E712
                UploadSession.created_at < cutoff,
            )
            .limit(settings.maintenance_batch_size)
        ).all()
    )
    by_id = {r.id: r for r in rows + older}
    deleted_objects = 0
    deleted_docs = 0
    for sess in by_id.values():
        doc = session.get(Document, sess.document_id)
        if doc is not None and doc.status not in {
            DocumentStatus.UPLOAD_PENDING,
            DocumentStatus.UPLOADED,
        }:
            # Do not touch ready/processing docs.
            continue
        if settings.maintenance_dry_run:
            continue
        try:
            storage.delete(sess.object_key)
            deleted_objects += 1
        except Exception:
            pass
        if doc is not None and doc.status == DocumentStatus.UPLOAD_PENDING:
            doc.status = DocumentStatus.DELETED
            doc.deleted_at = now
            doc.updated_at = now
            doc.status_message = "Abandoned upload cleaned"
            session.add(doc)
            deleted_docs += 1
        session.delete(sess)
    if not settings.maintenance_dry_run:
        session.commit()
    return {
        "sessions_seen": len(by_id),
        "objects_deleted": deleted_objects,
        "documents_marked_deleted": deleted_docs,
        "dry_run": settings.maintenance_dry_run,
    }


def cleanup_orphan_storage(
    session: Session,
    storage: ObjectStorage,
    settings: Settings,
    *,
    owner_id: str | None = None,
) -> dict[str, Any]:
    """Delete object keys under users/ that have no matching document row."""
    prefix = f"users/{owner_id}/" if owner_id else "users/"
    items, _ = storage.list_prefix(prefix)
    deleted = 0
    scanned = 0
    for item in items[: settings.maintenance_batch_size]:
        key = item.get("Key")
        if not key:
            continue
        scanned += 1
        # Expected key pattern: users/{owner}/documents/{doc_id}/...
        parts = key.split("/")
        doc_id = None
        if len(parts) >= 4 and parts[0] == "users" and parts[2] == "documents":
            doc_id = parts[3]
        if doc_id is None:
            continue
        doc = session.get(Document, doc_id)
        if doc is not None and doc.status != DocumentStatus.DELETED:
            continue
        if settings.maintenance_dry_run:
            continue
        try:
            storage.delete(key)
            deleted += 1
        except Exception:
            pass
    return {
        "scanned": scanned,
        "deleted": deleted,
        "dry_run": settings.maintenance_dry_run,
    }


def cleanup_orphan_vectors(
    session: Session,
    vectors: VectorStore,
    settings: Settings,
) -> dict[str, Any]:
    """
    Remove Pinecone vectors for deleted docs or non-active generations.
    Never deletes the document's current active_generation vectors.
    """
    deleted_docs = list(
        session.exec(
            select(Document)
            .where(col(Document.status) == DocumentStatus.DELETED)
            .limit(settings.maintenance_batch_size)
        ).all()
    )
    removed = 0
    for doc in deleted_docs:
        gens = {doc.active_generation}
        if doc.pending_generation:
            gens.add(doc.pending_generation)
        for gen in gens:
            if not gen:
                continue
            if settings.maintenance_dry_run:
                continue
            try:
                vectors.delete_by_document_generation(
                    namespace=doc.owner_id,
                    document_id=doc.id,
                    generation=gen,
                )
                removed += 1
            except Exception:
                pass

    # Stale chunk generations still marked active while doc advanced.
    stale_chunks = list(
        session.exec(
            select(Chunk).where(Chunk.state == "active").limit(settings.maintenance_batch_size * 5)
        ).all()
    )
    stale_removed = 0
    for chunk in stale_chunks:
        doc = session.get(Document, chunk.document_id)
        if doc is None:
            continue
        if doc.status == DocumentStatus.DELETED:
            continue
        if chunk.generation == doc.active_generation:
            continue
        if settings.maintenance_dry_run:
            continue
        try:
            vectors.delete_by_document_generation(
                namespace=chunk.owner_id,
                document_id=chunk.document_id,
                generation=chunk.generation,
            )
            chunk.state = "deleted"
            session.add(chunk)
            stale_removed += 1
        except Exception:
            pass
    if not settings.maintenance_dry_run and stale_removed:
        session.commit()
    return {
        "deleted_doc_vector_batches": removed,
        "stale_generation_batches": stale_removed,
        "dry_run": settings.maintenance_dry_run,
    }
