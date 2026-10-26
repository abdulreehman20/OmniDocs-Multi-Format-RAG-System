from fastapi import APIRouter, Depends, HTTPException
from propelauth_fastapi import User as AuthUser
from sqlmodel import Session, select

from src.auth import auth
from src.db import get_session
from src.models.item import Item, ItemCreate, ItemUpdate
from src.models.user import User

router = APIRouter(prefix="/items", tags=["items"])


def _ensure_user(session: Session, auth_user: AuthUser) -> User:
    user = session.get(User, auth_user.user_id)
    if user is None:
        user = User(
            id=auth_user.user_id,
            email=getattr(auth_user, "email", None),
            first_name=getattr(auth_user, "first_name", None),
            last_name=getattr(auth_user, "last_name", None),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.post("", response_model=Item, status_code=201)
def create_item(
    body: ItemCreate,
    session: Session = Depends(get_session),
    current_user: AuthUser = Depends(auth.require_user),
) -> Item:
    owner = _ensure_user(session, current_user)
    item = Item(name=body.name, description=body.description, owner_id=owner.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.patch("/{item_id}", response_model=Item)
def update_item(
    item_id: int,
    body: ItemUpdate,
    session: Session = Depends(get_session),
    current_user: AuthUser = Depends(auth.require_user),
) -> Item:
    item = session.get(Item, item_id)
    if item is None or item.owner_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Item not found")
    item.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: AuthUser = Depends(auth.require_user),
) -> None:
    item = session.get(Item, item_id)
    if item is None or item.owner_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()