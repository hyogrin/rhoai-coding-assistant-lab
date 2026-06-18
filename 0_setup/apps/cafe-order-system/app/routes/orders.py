from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderItem, MenuItem, OrderStatus
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services.order_service import calculate_order_total, validate_order_items
from app.config import MAX_ITEMS_PER_ORDER

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("/", response_model=list[OrderResponse])
def list_orders(
    status: OrderStatus | None = None,
    customer_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    if customer_id:
        query = query.filter(Order.customer_id == customer_id)
    return query.order_by(Order.created_at.desc()).limit(limit).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    if len(order_data.items) > MAX_ITEMS_PER_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_ITEMS_PER_ORDER} items per order",
        )

    unavailable = validate_order_items(db, order_data.items)
    if unavailable:
        raise HTTPException(
            status_code=400,
            detail=f"Unavailable items: {unavailable}",
        )

    order = Order(
        customer_id=order_data.customer_id,
        notes=order_data.notes,
    )
    db.add(order)
    db.flush()

    for item_data in order_data.items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_data.menu_item_id,
            quantity=item_data.quantity,
            customization=item_data.customization,
        )
        db.add(order_item)

    order.total_amount = calculate_order_total(db, order_data.items)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
        OrderStatus.PREPARING: [OrderStatus.READY],
        OrderStatus.READY: [OrderStatus.PICKED_UP],
    }

    allowed = valid_transitions.get(order.status, [])
    if status_update.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {order.status} to {status_update.status}",
        )

    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", status_code=204)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
        raise HTTPException(
            status_code=400,
            detail="Can only cancel pending or confirmed orders",
        )
    order.status = OrderStatus.CANCELLED
    db.commit()
