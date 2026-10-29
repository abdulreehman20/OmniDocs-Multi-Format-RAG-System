from fastapi import APIRouter

from src.api.v1 import auth, chat, conversations, documents, health, limits, me, uploads

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(limits.router)
api_router.include_router(uploads.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(me.router)
