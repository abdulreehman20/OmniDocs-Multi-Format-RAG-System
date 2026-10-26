from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Item(SQLModel, table=True):
    __tablename__ = "items"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str | None = None
    owner_id: str = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ItemCreate(SQLModel):
    name: str
    description: str | None = None


class ItemUpdate(SQLModel):
    name: str | None = None
    description: str | None = None