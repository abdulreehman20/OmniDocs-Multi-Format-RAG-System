from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

import inngest
from src.db.models import OutboxEvent
from src.inngest.client import get_inngest_client


def create_outbox_event(
    session: Session,
    *,
    event_name: str,
    payload: dict[str, Any],
) -> OutboxEvent:
    event = OutboxEvent(
        event_name=event_name,
        payload=payload,
        dispatch_state="pending",
        attempts=0,
    )
    session.add(event)
    return event


def try_dispatch_outbox(session: Session, event: OutboxEvent) -> None:
    """Best-effort Inngest send. Failures leave the row pending for Phase 2 reconciliation."""
    event.attempts += 1
    try:
        client = get_inngest_client()
        ids = client.send_sync(
            inngest.Event(name=event.event_name, data=event.payload),
        )
        event.inngest_event_id = str(ids[0]) if ids else None
        event.dispatch_state = "dispatched"
        event.dispatched_at = datetime.now(UTC)
    except Exception:
        event.dispatch_state = "pending"
    session.add(event)
    session.commit()
