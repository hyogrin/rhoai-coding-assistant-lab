from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MenuItem, MenuCategory
from app.schemas import MenuItemCreate, MenuItemResponse

router = APIRouter(prefix="/api/menu", tags=["menu"])


@router.get("/", response_model=list[MenuItemResponse])
def list_menu_items(
    category: MenuCategory | None = None,
    available_only: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(MenuItem)
    if category:
        query = query.filter(MenuItem.category == category)
    if available_only:
        query = query.filter(MenuItem.is_available == True)  # noqa: E712
    return query.all()


@router.get("/{item_id}", response_model=MenuItemResponse)
def get_menu_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.post("/", response_model=MenuItemResponse, status_code=201)
def create_menu_item(item: MenuItemCreate, db: Session = Depends(get_db)):
    db_item = MenuItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/{item_id}/availability")
def toggle_availability(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.is_available = not item.is_available
    db.commit()
    return {"id": item_id, "is_available": item.is_available}


@router.get("/search/", response_model=list[MenuItemResponse])
def search_menu(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    return (
        db.query(MenuItem)
        .filter(MenuItem.name.ilike(f"%{q}%") | MenuItem.description.ilike(f"%{q}%"))
        .all()
    )
