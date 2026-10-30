from fastapi import APIRouter

from src.api.deps import CurrentUser, DbSession
from src.schemas.me import MeResponse, MeUpdate
from src.services import users as users_service

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
def get_me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(**users_service.user_to_dict(current_user))


@router.patch("", response_model=MeResponse)
def patch_me(
    body: MeUpdate,
    session: DbSession,
    current_user: CurrentUser,
) -> MeResponse:
    user = users_service.update_user_profile(
        session,
        current_user,
        display_name=body.display_name,
        preferences=body.preferences,
    )
    return MeResponse(**users_service.user_to_dict(user))
