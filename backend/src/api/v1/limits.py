from fastapi import APIRouter

from src.api.deps import AppSettings, CurrentUser
from src.schemas.documents import LimitsResponse
from src.services.file_types import accept_attribute

router = APIRouter(tags=["limits"])


@router.get("/limits", response_model=LimitsResponse)
def get_limits(settings: AppSettings, current_user: CurrentUser) -> LimitsResponse:
    _ = current_user
    return LimitsResponse(
        max_file_size_bytes=settings.max_file_size_bytes,
        max_files_per_selection=settings.max_files_per_selection,
        accepted_extensions=accept_attribute(),
    )
