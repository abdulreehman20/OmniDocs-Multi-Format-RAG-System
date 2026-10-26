from fastapi import APIRouter

from src.api.v1 import health, items, whoami

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(whoami.router)
api_router.include_router(items.router)