from fastapi import APIRouter, HTTPException, status

from src.api.deps import AppSettings, CurrentUser, DbSession, Storage
from src.schemas.documents import DocumentResponse, DownloadResponse, IngestionJobResponse
from src.services import documents as documents_service
from src.services import ingestion as ingestion_service
from src.services import uploads as uploads_service
from src.services.ingestion import IngestionConflictError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
def list_documents(session: DbSession, current_user: CurrentUser) -> list[DocumentResponse]:
    docs = documents_service.list_documents(session, current_user.id)
    return [DocumentResponse(**documents_service.document_to_dict(d)) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    session: DbSession,
    current_user: CurrentUser,
) -> DocumentResponse:
    doc = documents_service.get_owned_document(session, current_user.id, document_id)
    return DocumentResponse(**documents_service.document_to_dict(doc))


@router.get("/{document_id}/jobs/latest", response_model=IngestionJobResponse)
def get_latest_job(
    document_id: str,
    session: DbSession,
    current_user: CurrentUser,
) -> IngestionJobResponse:
    documents_service.get_owned_document(session, current_user.id, document_id)
    job = ingestion_service.latest_job_for_document(session, document_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        generation=job.generation,
        status=job.status,
        stage=job.stage,
        attempts=job.attempts,
        error_code=job.error_code,
        error_message=job.error_message,
        progress=job.progress or {},
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        created_at=job.created_at.isoformat(),
    )


@router.post("/{document_id}/complete", response_model=DocumentResponse, status_code=202)
def complete_document(
    document_id: str,
    session: DbSession,
    storage: Storage,
    settings: AppSettings,
    current_user: CurrentUser,
) -> DocumentResponse:
    doc = uploads_service.complete_upload(
        session,
        storage,
        settings,
        owner_id=current_user.id,
        document_id=document_id,
    )
    return DocumentResponse(**documents_service.document_to_dict(doc))


@router.post("/{document_id}/retry", response_model=DocumentResponse, status_code=202)
def retry_document(
    document_id: str,
    session: DbSession,
    settings: AppSettings,
    current_user: CurrentUser,
) -> DocumentResponse:
    try:
        doc = ingestion_service.retry_document(
            session,
            settings,
            owner_id=current_user.id,
            document_id=document_id,
        )
    except IngestionConflictError as exc:
        code = (
            status.HTTP_404_NOT_FOUND
            if exc.code == "not_found"
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc
    return DocumentResponse(**documents_service.document_to_dict(doc))


@router.get("/{document_id}/download", response_model=DownloadResponse)
def download_document(
    document_id: str,
    session: DbSession,
    storage: Storage,
    settings: AppSettings,
    current_user: CurrentUser,
) -> DownloadResponse:
    result = documents_service.create_download_url(
        session,
        storage,
        settings,
        owner_id=current_user.id,
        document_id=document_id,
    )
    return DownloadResponse(**result)


@router.post("/{document_id}/delete", response_model=DocumentResponse)
def delete_document(
    document_id: str,
    session: DbSession,
    storage: Storage,
    current_user: CurrentUser,
) -> DocumentResponse:
    doc = documents_service.request_delete(
        session,
        storage,
        owner_id=current_user.id,
        document_id=document_id,
    )
    return DocumentResponse(**documents_service.document_to_dict(doc))

