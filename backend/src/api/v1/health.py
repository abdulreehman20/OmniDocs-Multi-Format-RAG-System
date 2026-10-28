from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from src.db import engine

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Liveness: process is up. Does not check dependencies."""
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready() -> dict[str, str]:
    """Readiness: database is reachable. No provider details in the response."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="not ready",
        ) from None
    return {"status": "ok"}
