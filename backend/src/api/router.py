from fastapi import APIRouter

from src.api.v1 import health, items

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(items.router)
