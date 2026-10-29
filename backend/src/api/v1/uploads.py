from fastapi import APIRouter

from src.api.deps import AppSettings, CurrentUser, DbSession, Storage
from src.schemas.documents import UploadInitRequest, UploadInitResponse
from src.services import uploads as uploads_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/init", response_model=UploadInitResponse)
def upload_init(
    body: UploadInitRequest,
    session: DbSession,
    storage: Storage,
    settings: AppSettings,
    current_user: CurrentUser,
) -> UploadInitResponse:
    result = uploads_service.init_upload(
        session,
        storage,
        settings,
        owner_id=current_user.id,
        filename=body.filename,
        mime_type=body.mime_type,
        byte_size=body.byte_size,
        idempotency_key=body.idempotency_key,
        client_checksum=body.client_checksum,
    )
    return UploadInitResponse(**result)
