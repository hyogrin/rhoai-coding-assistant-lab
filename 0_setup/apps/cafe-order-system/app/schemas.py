from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import MenuCategory, OrderStatus


class MenuItemCreate(BaseModel):
    name: str = Field(..., max_length=100)
    category: MenuCategory
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    calories: Optional[int] = None
    allergens: Optional[str] = None


class MenuItemResponse(BaseModel):
    id: int
    name: str
    category: MenuCategory
    price: float
    description: Optional[str]
    is_available: bool
    calories: Optional[int]
    allergens: Optional[str]

    model_config = {"from_attributes": True}


class CustomerCreate(BaseModel):
    employee_id: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int
    employee_id: str
    name: str
    department: Optional[str]
    email: Optional[str]
    registered_at: datetime

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1)
    customization: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    customization: Optional[str]
    menu_item: MenuItemResponse

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: OrderStatus
    total_amount: float
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]

    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
