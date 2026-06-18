from sqlalchemy.orm import Session

from app.models import MenuItem
from app.schemas import OrderItemCreate


def validate_order_items(db: Session, items: list[OrderItemCreate]) -> list[str]:
    """Return names of unavailable menu items."""
    unavailable = []
    for item in items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
        if not menu_item:
            unavailable.append(f"ID:{item.menu_item_id} (not found)")
        elif not menu_item.is_available:
            unavailable.append(menu_item.name)
    return unavailable


def calculate_order_total(db: Session, items: list[OrderItemCreate]) -> float:
    """Calculate the total price for all order items."""
    total = 0.0
    for item in items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
        if menu_item:
            total += menu_item.price * item.quantity
    return round(total, 2)
