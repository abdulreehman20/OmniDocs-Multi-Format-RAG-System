from fastapi import APIRouter, Depends
from propelauth_fastapi import User

from src.auth import auth

router = APIRouter(tags=["auth"])


@router.get("/whoami")
async def whoami(current_user: User = Depends(auth.require_user)):
    return {"user_id": current_user.user_id}
