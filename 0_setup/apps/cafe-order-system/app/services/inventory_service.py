from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import MenuItem, OrderItem, Order, OrderStatus, MenuCategory


def get_popular_items(db: Session, limit: int = 5) -> list[dict]:
    """Get most ordered menu items (excluding cancelled orders)."""
    results = (
        db.query(
            MenuItem.name,
            MenuItem.category,
            func.sum(OrderItem.quantity).label("total_ordered"),
        )
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status != OrderStatus.CANCELLED)
        .group_by(MenuItem.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [
        {"name": r.name, "category": r.category, "total_ordered": r.total_ordered}
        for r in results
    ]


def get_category_summary(db: Session) -> list[dict]:
    """Get count of available items per category."""
    results = (
        db.query(
            MenuItem.category,
            func.count(MenuItem.id).label("count"),
        )
        .filter(MenuItem.is_available == True)  # noqa: E712
        .group_by(MenuItem.category)
        .all()
    )
    return [{"category": r.category, "available_count": r.count} for r in results]


def check_low_availability(db: Session) -> list[str]:
    """Return categories with fewer than 2 available items."""
    summary = get_category_summary(db)
    return [s["category"] for s in summary if s["available_count"] < 2]
