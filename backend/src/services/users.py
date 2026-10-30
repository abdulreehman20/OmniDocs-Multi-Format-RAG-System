from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session

from src.db.models import User


def upsert_user_from_claims(
    session: Session,
    *,
    user_id: str,
    email: str | None = None,
    display_name: str | None = None,
) -> User:
    user = session.get(User, user_id)
    now = datetime.now(UTC)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            display_name=display_name,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
    else:
        if email is not None:
            user.email = email
        if display_name is not None:
            user.display_name = display_name
        user.updated_at = now
        session.add(user)
    session.commit()
    session.refresh(user)
    return user


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "preferences": dict(user.preferences or {}),
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def update_user_profile(
    session: Session,
    user: User,
    *,
    display_name: str | None = None,
    preferences: dict[str, Any] | None = None,
) -> User:
    if display_name is not None:
        user.display_name = display_name.strip() or None
    if preferences is not None:
        user.preferences = dict(preferences)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
