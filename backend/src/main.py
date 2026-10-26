from fastapi import FastAPI

from src.api.router import api_router

app = FastAPI(title="backend")
app.include_router(api_router)
