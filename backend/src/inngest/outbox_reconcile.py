from sqlmodel import Session

import inngest
from src.db.session import engine
from src.inngest.client import get_inngest_client
from src.services import ingestion as ingestion_service
from src.services.outbox import try_dispatch_outbox

client = get_inngest_client()


@client.create_function(
    fn_id="outbox-reconcile",
    trigger=inngest.TriggerEvent(event="maintenance/reconcile.requested.v1"),
)
def reconcile_outbox(ctx: inngest.ContextSync) -> dict:
    _ = ctx

    def run() -> dict:
        dispatched = 0
        with Session(engine) as session:
            events = ingestion_service.pending_outbox_events(session, limit=50)
            for event in events:
                try_dispatch_outbox(session, event)
                session.refresh(event)
                if event.dispatch_state == "dispatched":
                    dispatched += 1
        return {"pending_seen": len(events), "dispatched": dispatched}

    return ctx.step.run("dispatch-pending", run)
