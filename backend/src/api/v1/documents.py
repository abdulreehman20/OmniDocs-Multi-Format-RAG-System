from fastapi import APIRouter

from src.api.deps import AppSettings, CurrentUser, DbSession, Storage
from src.schemas.documents import DocumentResponse, DownloadResponse
from src.services import documents as documents_service
from src.services import uploads as uploads_service

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
