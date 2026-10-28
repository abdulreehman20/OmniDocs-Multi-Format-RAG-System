from fastapi import FastAPI
from inngest.fast_api import serve

from src.inngest.client import get_inngest_client
from src.inngest.smoke import demo_hello


def register_inngest(app: FastAPI) -> None:
    serve(
        app,
        get_inngest_client(),
        [demo_hello],
    )
