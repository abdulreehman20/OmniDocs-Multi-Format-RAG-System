from sqlmodel import Session

import inngest
from src.config import get_settings
from src.db.session import engine
from src.inngest.client import get_inngest_client
from src.services.maintenance import dispatch_pending_outbox

client = get_inngest_client()


def run_outbox_reconcile(*, limit: int | None = None) -> dict:
    settings = get_settings()
    batch = limit or settings.maintenance_batch_size
    with Session(engine) as session:
        return dispatch_pending_outbox(session, limit=batch)


@client.create_function(
    fn_id="outbox-reconcile",
    trigger=inngest.TriggerEvent(event="maintenance/reconcile.requested.v1"),
)
def reconcile_outbox(ctx: inngest.ContextSync) -> dict:
    return ctx.step.run("dispatch-pending", run_outbox_reconcile)


@client.create_function(
    fn_id="outbox-reconcile-cron",
    trigger=inngest.TriggerCron(cron="*/5 * * * *"),
)
def reconcile_outbox_cron(ctx: inngest.ContextSync) -> dict:
    # Shared helper — do not call the decorated Function as a Python function.
    return ctx.step.run("dispatch-pending", run_outbox_reconcile)
