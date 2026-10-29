from sqlmodel import Session

import inngest
from src.config import get_settings
from src.db.session import engine
from src.inngest.client import get_inngest_client
from src.observability.correlation import set_sentry_context
from src.providers.runtime import get_object_storage, get_vector_store
from src.services import maintenance as maintenance_service

client = get_inngest_client()


def _run_abandoned() -> dict:
    settings = get_settings()
    storage = get_object_storage()
    with Session(engine) as session:
        return maintenance_service.cleanup_abandoned_uploads(session, storage, settings)


def _run_orphan_storage(owner_id: str | None = None) -> dict:
    settings = get_settings()
    storage = get_object_storage()
    with Session(engine) as session:
        return maintenance_service.cleanup_orphan_storage(
            session, storage, settings, owner_id=owner_id
        )


def _run_orphan_vectors() -> dict:
    settings = get_settings()
    vectors = get_vector_store()
    with Session(engine) as session:
        return maintenance_service.cleanup_orphan_vectors(session, vectors, settings)


@client.create_function(
    fn_id="abandoned-uploads-cleanup",
    trigger=inngest.TriggerEvent(event="maintenance/abandoned-uploads.cleanup.v1"),
)
def abandoned_uploads_cleanup(ctx: inngest.ContextSync) -> dict:
    run_id = getattr(ctx, "run_id", None)
    set_sentry_context(inngest_run_id=str(run_id) if run_id else None)
    return ctx.step.run("cleanup-abandoned-uploads", _run_abandoned)


@client.create_function(
    fn_id="abandoned-uploads-cleanup-cron",
    trigger=inngest.TriggerCron(cron="0 * * * *"),
)
def abandoned_uploads_cleanup_cron(ctx: inngest.ContextSync) -> dict:
    run_id = getattr(ctx, "run_id", None)
    set_sentry_context(inngest_run_id=str(run_id) if run_id else None)
    return ctx.step.run("cleanup-abandoned-uploads", _run_abandoned)


@client.create_function(
    fn_id="orphan-storage-cleanup",
    trigger=inngest.TriggerEvent(event="maintenance/orphan-storage.cleanup.v1"),
)
def orphan_storage_cleanup(ctx: inngest.ContextSync) -> dict:
    run_id = getattr(ctx, "run_id", None)
    set_sentry_context(inngest_run_id=str(run_id) if run_id else None)
    owner_id = None
    if isinstance(getattr(ctx.event, "data", None), dict):
        owner_id = ctx.event.data.get("owner_id")

    def run() -> dict:
        return _run_orphan_storage(str(owner_id) if owner_id else None)

    return ctx.step.run("cleanup-orphan-storage", run)


@client.create_function(
    fn_id="orphan-storage-cleanup-cron",
    trigger=inngest.TriggerCron(cron="15 3 * * *"),
)
def orphan_storage_cleanup_cron(ctx: inngest.ContextSync) -> dict:
    run_id = getattr(ctx, "run_id", None)
    set_sentry_context(inngest_run_id=str(run_id) if run_id else None)
    return ctx.step.run("cleanup-orphan-storage", _run_orphan_storage)


@client.create_function(
    fn_id="orphan-vectors-cleanup",
    trigger=inngest.TriggerEvent(event="maintenance/orphan-vectors.cleanup.v1"),
)
def orphan_vectors_cleanup(ctx: inngest.ContextSync) -> dict:
    run_id = getattr(ctx, "run_id", None)
    set_sentry_context(inngest_run_id=str(run_id) if run_id else None)
    return ctx.step.run("cleanup-orphan-vectors", _run_orphan_vectors)


@client.create_function(
    fn_id="orphan-vectors-cleanup-cron",
    trigger=inngest.TriggerCron(cron="45 3 * * *"),
)
def orphan_vectors_cleanup_cron(ctx: inngest.ContextSync) -> dict:
    run_id = getattr(ctx, "run_id", None)
    set_sentry_context(inngest_run_id=str(run_id) if run_id else None)
    return ctx.step.run("cleanup-orphan-vectors", _run_orphan_vectors)
