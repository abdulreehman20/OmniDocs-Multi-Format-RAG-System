from sqlmodel import SQLModel


class ItemCreate(SQLModel):
    name: str
    description: str = ""


class ItemUpdate(SQLModel):
    name: str | None = None
    description: str | None = None


class Item(SQLModel):
    id: int
    name: str
    description: str = ""
