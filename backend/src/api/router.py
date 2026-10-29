from fastapi import APIRouter

from src.api.v1 import auth, documents, health, limits, uploads

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(limits.router)
api_router.include_router(uploads.router)
api_router.include_router(documents.router)
