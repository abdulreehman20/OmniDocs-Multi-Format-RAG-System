from datetime import UTC, datetime

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
