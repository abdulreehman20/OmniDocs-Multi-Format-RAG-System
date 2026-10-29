from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, col, select

from src.config import Settings
from src.db.models import Document, DocumentStatus
from src.providers.protocols import ObjectStorage
from src.services.ingestion import cancel_jobs_for_document
from src.services.outbox import create_outbox_event, try_dispatch_outbox


def get_owned_document(session: Session, owner_id: str, document_id: str) -> Document:
    doc = session.get(Document, document_id)
    if doc is None or doc.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return doc


def list_documents(session: Session, owner_id: str) -> list[Document]:
    statement = (
        select(Document)
        .where(Document.owner_id == owner_id)
        .where(col(Document.status) != DocumentStatus.DELETED)
        .order_by(col(Document.updated_at).desc())
    )
    return list(session.exec(statement).all())


def create_download_url(
    session: Session,
    storage: ObjectStorage,
    settings: Settings,
    *,
    owner_id: str,
    document_id: str,
) -> dict:
    doc = get_owned_document(session, owner_id, document_id)
    if doc.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if doc.status == DocumentStatus.UPLOAD_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="upload_incomplete")
    url = storage.create_download_url(doc.object_key, settings.download_url_expires_seconds)
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "download_url": url,
        "expires_seconds": settings.download_url_expires_seconds,
    }


def request_delete(
    session: Session,
    storage: ObjectStorage,
    *,
    owner_id: str,
    document_id: str,
) -> Document:
    doc = get_owned_document(session, owner_id, document_id)
    if doc.status == DocumentStatus.DELETED:
        return doc

    now = datetime.now(UTC)
    doc.status = DocumentStatus.DELETING
    doc.updated_at = now
    doc.status_message = "Deleting"
    cancel_jobs_for_document(session, document_id)
    outbox = create_outbox_event(
        session,
        event_name="document/delete.requested.v1",
        payload={
            "document_id": doc.id,
            "owner_id": owner_id,
            "object_key": doc.object_key,
            "generation": doc.active_generation,
        },
    )
    session.add(doc)
    session.add(outbox)
    session.commit()
    session.refresh(doc)
    session.refresh(outbox)

    cleanup_ok = False
    try:
        storage.delete(doc.object_key)
        cleanup_ok = True
    except Exception:
        cleanup_ok = False

    if cleanup_ok:
        doc.status = DocumentStatus.DELETED
        doc.deleted_at = datetime.now(UTC)
        doc.updated_at = datetime.now(UTC)
        doc.status_message = "Deleted"
        session.add(doc)
        session.commit()
        outbox.dispatch_state = "dispatched"
        outbox.dispatched_at = datetime.now(UTC)
        session.add(outbox)
        session.commit()
    else:
        try_dispatch_outbox(session, outbox)

    session.refresh(doc)
    return doc


def document_to_dict(doc: Document) -> dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "source_type": doc.source_type,
        "mime_type": doc.mime_type,
        "byte_size": doc.byte_size,
        "status": doc.status,
        "ingestion_stage": doc.ingestion_stage,
        "ingestion_progress": doc.ingestion_progress,
        "error_code": doc.error_code,
        "error_message": doc.error_message,
        "status_message": doc.status_message,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }
