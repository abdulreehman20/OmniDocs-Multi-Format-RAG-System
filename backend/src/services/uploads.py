from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlmodel import Session, select

from src.config import Settings
from src.db.models import Document, DocumentStatus, IngestionJob, UploadSession
from src.providers.protocols import ObjectStorage
from src.services.file_types import resolve_upload_type
from src.services.outbox import create_outbox_event, try_dispatch_outbox


def object_key_for(user_id: str, document_id: str) -> str:
    return f"users/{user_id}/documents/{document_id}/original"


def init_upload(
    session: Session,
    storage: ObjectStorage,
    settings: Settings,
    *,
    owner_id: str,
    filename: str,
    mime_type: str,
    byte_size: int,
    idempotency_key: str,
    client_checksum: str | None = None,
) -> dict:
    if byte_size <= 0 or byte_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_file_size",
        )

    existing = session.exec(
        select(UploadSession).where(UploadSession.idempotency_key == idempotency_key)
    ).first()
    if existing:
        doc = session.get(Document, existing.document_id)
        if doc is None or doc.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        if existing.completed:
            return {
                "document_id": doc.id,
                "upload_session_id": existing.id,
                "status": doc.status,
                "put_url": None,
                "object_key": doc.object_key,
                "expires_seconds": settings.upload_url_expires_seconds,
            }
        put_url = storage.create_upload_url(
            existing.object_key,
            existing.mime_type,
            settings.upload_url_expires_seconds,
        )
        return {
            "document_id": doc.id,
            "upload_session_id": existing.id,
            "status": doc.status,
            "put_url": put_url,
            "object_key": doc.object_key,
            "expires_seconds": settings.upload_url_expires_seconds,
        }

    try:
        source_type, canonical_mime = resolve_upload_type(filename, mime_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    document_id = str(uuid4())
    key = object_key_for(owner_id, document_id)
    now = datetime.now(UTC)
    doc = Document(
        id=document_id,
        owner_id=owner_id,
        filename=filename,
        source_type=source_type.value,
        mime_type=canonical_mime,
        byte_size=byte_size,
        object_bucket=settings.s3_bucket_documents,
        object_key=key,
        status=DocumentStatus.UPLOAD_PENDING,
        created_at=now,
        updated_at=now,
    )
    upload = UploadSession(
        document_id=document_id,
        owner_id=owner_id,
        expected_size=byte_size,
        mime_type=canonical_mime,
        object_key=key,
        expires_at=now + timedelta(seconds=settings.upload_url_expires_seconds),
        completed=False,
        client_checksum=client_checksum,
        idempotency_key=idempotency_key,
        created_at=now,
    )
    session.add(doc)
    session.add(upload)
    session.commit()
    session.refresh(doc)
    session.refresh(upload)

    put_url = storage.create_upload_url(
        key,
        canonical_mime,
        settings.upload_url_expires_seconds,
    )
    return {
        "document_id": doc.id,
        "upload_session_id": upload.id,
        "status": doc.status,
        "put_url": put_url,
        "object_key": doc.object_key,
        "expires_seconds": settings.upload_url_expires_seconds,
    }


def complete_upload(
    session: Session,
    storage: ObjectStorage,
    settings: Settings,
    *,
    owner_id: str,
    document_id: str,
) -> Document:
    _ = settings
    doc = session.get(Document, document_id)
    if doc is None or doc.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if doc.status in {
        DocumentStatus.QUEUED,
        DocumentStatus.PROCESSING,
        DocumentStatus.READY,
    }:
        return doc

    if doc.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="document_deleted")

    upload = session.exec(
        select(UploadSession)
        .where(UploadSession.document_id == document_id)
        .where(UploadSession.owner_id == owner_id)
        .order_by(UploadSession.created_at.desc())
    ).first()
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if upload.expires_at < datetime.now(UTC) and not upload.completed:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="upload_expired")

    try:
        head = storage.head(doc.object_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="object_missing",
        ) from exc

    actual_size = int(head.get("ContentLength") or 0)
    if actual_size != upload.expected_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="size_mismatch",
        )

    now = datetime.now(UTC)
    job = IngestionJob(
        owner_id=owner_id,
        document_id=doc.id,
        generation=1,
        status="queued",
        stage="queued",
        attempts=0,
        correlation_id=str(uuid4()),
        created_at=now,
    )
    upload.completed = True
    upload.uploaded_size = actual_size
    upload.etag = head.get("ETag")
    doc.byte_size = actual_size
    doc.status = DocumentStatus.QUEUED
    doc.ingestion_stage = "queued"
    doc.pending_generation = 1
    doc.updated_at = now
    doc.status_message = "Queued for ingestion"

    outbox = create_outbox_event(
        session,
        event_name="document/uploaded.v1",
        payload={
            "document_id": doc.id,
            "owner_id": owner_id,
            "object_key": doc.object_key,
            "generation": 1,
            "job_id": job.id,
        },
    )
    session.add(job)
    session.add(upload)
    session.add(doc)
    session.add(outbox)
    session.commit()
    session.refresh(doc)
    session.refresh(outbox)
    session.refresh(job)

    try_dispatch_outbox(session, outbox)
    if outbox.inngest_event_id:
        job.inngest_event_id = outbox.inngest_event_id
        session.add(job)
        session.commit()

    session.refresh(doc)
    return doc
