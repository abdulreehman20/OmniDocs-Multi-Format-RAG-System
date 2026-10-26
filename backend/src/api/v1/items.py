from fastapi import APIRouter, HTTPException

from src.schemas.item import Item, ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])

items: dict[int, Item] = {}
_next_id = 1


@router.get("", response_model=list[Item])
def list_items() -> list[Item]:
    return list(items.values())


@router.post("", response_model=Item, status_code=201)
def create_item(body: ItemCreate) -> Item:
    global _next_id
    item = Item(id=_next_id, name=body.name, description=body.description)
    items[item.id] = item
    _next_id += 1
    return item


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    item = items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=Item)
def update_item(item_id: int, body: ItemUpdate) -> Item:
    item = items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = item.model_copy(update=body.model_dump(exclude_unset=True))
    items[item_id] = updated
    return updated


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int) -> None:
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    del items[item_id]


def _self_check() -> None:
    global _next_id
    items.clear()
    _next_id = 1
    created = create_item(ItemCreate(name="a", description="b"))
    assert created.id == 1
    updated = update_item(1, ItemUpdate(name="c"))
    assert updated.name == "c" and updated.description == "b"
    assert len(list_items()) == 1
    delete_item(1)
    try:
        get_item(1)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("expected 404")
    items.clear()
    _next_id = 1


if __name__ == "__main__":
    _self_check()
