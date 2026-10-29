from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session

from src.db.models import User


def bump_user_corpus_version(session: Session, owner_id: str) -> int:
    """Increment tenant corpus_version so retrieval cache keys go stale."""
    user = session.get(User, owner_id)
    if user is None:
        return 0
    user.corpus_version = (user.corpus_version or 0) + 1
    user.updated_at = datetime.now(UTC)
    session.add(user)
    # Caller commits (often with other rows).
    return user.corpus_version


def get_user_corpus_version(session: Session, owner_id: str) -> int:
    user = session.get(User, owner_id)
    if user is None:
        return 0
    return int(user.corpus_version or 0)
