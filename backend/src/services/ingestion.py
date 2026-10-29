from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, col, select

from src.ai.ingestion.pipeline import build_vector_id
from src.config import Settings
from src.db.models import (
    Chunk,
    Document,
    DocumentStatus,
    IngestionBatch,
    IngestionJob,
    OutboxEvent,
)
from src.services.outbox import create_outbox_event, try_dispatch_outbox


class IngestionConflictError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def get_job(session: Session, job_id: str) -> IngestionJob | None:
    return session.get(IngestionJob, job_id)


def latest_job_for_document(session: Session, document_id: str) -> IngestionJob | None:
    statement = (
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(col(IngestionJob.created_at).desc())
    )
    return session.exec(statement).first()


def claim_job(
    session: Session,
    *,
    document_id: str,
    job_id: str,
    generation: int,
) -> dict[str, Any]:
    doc = session.get(Document, document_id)
    job = session.get(IngestionJob, job_id)
    if doc is None or job is None:
        raise IngestionConflictError("not_found", "Document or job not found")
    if doc.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
        raise IngestionConflictError("document_deleted", "Document was deleted")
    if job.cancelled:
        raise IngestionConflictError("job_cancelled", "Job was cancelled")
    if job.document_id != document_id or job.generation != generation:
        raise IngestionConflictError("stale_job", "Job does not match document generation")
    if doc.pending_generation not in (None, generation) and doc.pending_generation != generation:
        raise IngestionConflictError("stale_generation", "Stale ingestion generation")

    now = datetime.now(UTC)
    doc.status = DocumentStatus.PROCESSING
    doc.ingestion_stage = "claimed"
    doc.ingestion_progress = 0.05
    doc.status_message = "Processing"
    doc.error_code = None
    doc.error_message = None
    doc.pending_generation = generation
    doc.updated_at = now

    job.status = "processing"
    job.stage = "claimed"
    job.attempts += 1
    job.started_at = job.started_at or now
    job.progress = {"stage": "claimed"}
    session.add(doc)
    session.add(job)
    session.commit()
    return {
        "document_id": doc.id,
        "owner_id": doc.owner_id,
        "object_key": doc.object_key,
        "source_type": doc.source_type,
        "generation": generation,
        "job_id": job.id,
        "byte_size": doc.byte_size,
    }


def update_progress(
    session: Session,
    *,
    document_id: str,
    job_id: str,
    stage: str,
    progress: float,
    message: str,
    extra: dict[str, Any] | None = None,
) -> None:
    doc = session.get(Document, document_id)
    job = session.get(IngestionJob, job_id)
    if doc is None or job is None:
        return
    if doc.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
        raise IngestionConflictError("document_deleted", "Document was deleted")
    if job.cancelled:
        raise IngestionConflictError("job_cancelled", "Job was cancelled")
    now = datetime.now(UTC)
    doc.ingestion_stage = stage
    doc.ingestion_progress = progress
    doc.status_message = message
    doc.status = DocumentStatus.PROCESSING
    doc.updated_at = now
    job.stage = stage
    job.status = "processing"
    job.progress = {"stage": stage, **(extra or {})}
    session.add(doc)
    session.add(job)
    session.commit()


def mark_failed(
    session: Session,
    *,
    document_id: str,
    job_id: str,
    error_code: str,
    error_message: str,
) -> None:
    doc = session.get(Document, document_id)
    job = session.get(IngestionJob, job_id)
    now = datetime.now(UTC)
    if doc is not None and doc.status not in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
        doc.status = DocumentStatus.FAILED
        doc.ingestion_stage = "failed"
        doc.error_code = error_code
        doc.error_message = error_message[:500]
        doc.status_message = error_message[:200]
        doc.updated_at = now
        session.add(doc)
    if job is not None:
        job.status = "failed"
        job.stage = "failed"
        job.error_code = error_code
        job.error_message = error_message[:500]
        job.finished_at = now
        session.add(job)
    session.commit()


def finalize_generation(
    session: Session,
    settings: Settings,
    *,
    document_id: str,
    job_id: str,
    generation: int,
    chunk_count: int,
    content_sha256: str,
) -> None:
    doc = session.get(Document, document_id)
    job = session.get(IngestionJob, job_id)
    if doc is None or job is None:
        raise IngestionConflictError("not_found", "Document or job not found")
    if doc.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
        raise IngestionConflictError("document_deleted", "Document was deleted")
    if job.cancelled:
        raise IngestionConflictError("job_cancelled", "Job was cancelled")

    now = datetime.now(UTC)
    doc.active_generation = generation
    doc.pending_generation = None
    doc.chunk_count = chunk_count
    doc.sha256 = content_sha256
    doc.parser_version = settings.parser_version
    doc.chunker_version = settings.chunker_version
    doc.embedding_model_id = settings.embedding_model_id
    doc.corpus_version = (doc.corpus_version or 0) + 1
    doc.status = DocumentStatus.READY
    doc.ingestion_stage = "ready"
    doc.ingestion_progress = 1.0
    doc.status_message = "Ready"
    doc.error_code = None
    doc.error_message = None
    doc.updated_at = now

    job.status = "succeeded"
    job.stage = "ready"
    job.finished_at = now
    job.progress = {"stage": "ready", "chunk_count": chunk_count}
    session.add(doc)
    session.add(job)
    session.commit()


def replace_chunk_rows(
    session: Session,
    *,
    owner_id: str,
    document_id: str,
    generation: int,
    rows: list[dict[str, Any]],
    embedding_model_id: str,
    chunker_version: str,
) -> int:
    existing = session.exec(
        select(Chunk).where(
            Chunk.document_id == document_id,
            Chunk.generation == generation,
        )
    ).all()
    for row in existing:
        session.delete(row)
    session.commit()

    for row in rows:
        chunk = Chunk(
            owner_id=owner_id,
            document_id=document_id,
            generation=generation,
            vector_id=row["vector_id"],
            chunk_index=row["chunk_index"],
            text=row.get("text"),
            text_sha256=row["text_sha256"],
            token_estimate=int(row.get("token_estimate") or 0),
            locator=row.get("locator") or {},
            chunker_version=chunker_version,
            embedding_model_id=embedding_model_id,
            state="active",
        )
        session.add(chunk)
    session.commit()
    return len(rows)


def upsert_batches(
    session: Session,
    *,
    job_id: str,
    document_id: str,
    generation: int,
    batch_keys: list[str],
) -> None:
    for i, key in enumerate(batch_keys):
        batch = IngestionBatch(
            job_id=job_id,
            document_id=document_id,
            generation=generation,
            batch_number=i,
            manifest_key=key,
            status="pending",
        )
        session.add(batch)
    session.commit()


def mark_batch_done(
    session: Session,
    *,
    job_id: str,
    batch_number: int,
    result: dict[str, Any],
) -> None:
    statement = select(IngestionBatch).where(
        IngestionBatch.job_id == job_id,
        IngestionBatch.batch_number == batch_number,
    )
    batch = session.exec(statement).first()
    if batch is None:
        return
    batch.status = "succeeded"
    batch.result = result
    batch.updated_at = datetime.now(UTC)
    session.add(batch)
    session.commit()


def retry_document(
    session: Session,
    settings: Settings,
    *,
    owner_id: str,
    document_id: str,
) -> Document:
    _ = settings
    doc = session.get(Document, document_id)
    if doc is None or doc.owner_id != owner_id:
        raise IngestionConflictError("not_found", "Not found")
    if doc.status != DocumentStatus.FAILED:
        raise IngestionConflictError("not_failed", "Only failed documents can be retried")
    if doc.pending_generation is not None:
        raise IngestionConflictError("already_pending", "Ingestion already pending")

    generation = max(doc.active_generation, 0) + 1
    job = IngestionJob(
        owner_id=owner_id,
        document_id=doc.id,
        generation=generation,
        status="queued",
        stage="queued",
    )
    outbox = create_outbox_event(
        session,
        event_name="document/uploaded.v1",
        payload={
            "document_id": doc.id,
            "owner_id": owner_id,
            "object_key": doc.object_key,
            "generation": generation,
            "job_id": job.id,
        },
    )
    now = datetime.now(UTC)
    doc.status = DocumentStatus.QUEUED
    doc.pending_generation = generation
    doc.ingestion_stage = "queued"
    doc.ingestion_progress = 0.0
    doc.error_code = None
    doc.error_message = None
    doc.status_message = "Queued for ingestion"
    doc.updated_at = now
    session.add(doc)
    session.add(job)
    session.add(outbox)
    session.commit()
    session.refresh(outbox)
    try_dispatch_outbox(session, outbox)
    if outbox.inngest_event_id:
        job.inngest_event_id = outbox.inngest_event_id
        session.add(job)
        session.commit()
    session.refresh(doc)
    return doc


def cancel_jobs_for_document(session: Session, document_id: str) -> None:
    jobs = session.exec(
        select(IngestionJob).where(
            IngestionJob.document_id == document_id,
            col(IngestionJob.status).in_(["queued", "processing"]),
        )
    ).all()
    for job in jobs:
        job.cancelled = True
        job.status = "cancelled"
        job.stage = "cancelled"
        session.add(job)
    session.commit()


def pending_outbox_events(session: Session, *, limit: int = 50) -> list[OutboxEvent]:
    statement = (
        select(OutboxEvent)
        .where(OutboxEvent.dispatch_state == "pending")
        .order_by(col(OutboxEvent.created_at).asc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def vector_id_for(document_id: str, generation: int, chunk_index: int) -> str:
    return build_vector_id(document_id, generation, chunk_index)
