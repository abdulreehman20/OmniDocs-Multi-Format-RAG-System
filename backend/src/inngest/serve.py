from fastapi import FastAPI
from inngest.fast_api import serve

from src.inngest.client import get_inngest_client
from src.inngest.delete_document import document_delete_requested
from src.inngest.ingestion import ingest_document_uploaded
from src.inngest.maintenance import (
    abandoned_uploads_cleanup,
    abandoned_uploads_cleanup_cron,
    orphan_storage_cleanup,
    orphan_storage_cleanup_cron,
    orphan_vectors_cleanup,
    orphan_vectors_cleanup_cron,
)
from src.inngest.outbox_reconcile import reconcile_outbox, reconcile_outbox_cron
from src.inngest.smoke import demo_hello


def register_inngest(app: FastAPI) -> None:
    serve(
        app,
        get_inngest_client(),
        [
            demo_hello,
            ingest_document_uploaded,
            document_delete_requested,
            reconcile_outbox,
            reconcile_outbox_cron,
            abandoned_uploads_cleanup,
            abandoned_uploads_cleanup_cron,
            orphan_storage_cleanup,
            orphan_storage_cleanup_cron,
            orphan_vectors_cleanup,
            orphan_vectors_cleanup_cron,
        ],
    )
