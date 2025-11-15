from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from .models import OrderStatus


# ===== Menu Schemas =====


class MenuItemBase(BaseModel):
    name: str = Field(..., description="Item name")
    unit_price: Decimal = Field(..., description="Unit price")


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    unit_price: Optional[Decimal] = None
    is_active: Optional[bool] = None


class MenuItemOut(MenuItemBase):
    id: int
    is_active: bool
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===== Order Schemas =====


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    customer_name: str
    items: List[OrderItemCreate]


class OrderItemOut(BaseModel):
    id: int
    menu_item_id: Optional[int]
    item_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    order_code: str
    customer_name: str
    status: OrderStatus
    total_price: Decimal
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


# ===== Stats Schemas =====


class ItemStats(BaseModel):
    item_name: str
    total_quantity: int
    total_amount: Decimal


class OrderStats(BaseModel):
    total_orders: int
    total_amount: Decimal
    items: List[ItemStats]


# ===== Common =====


class Message(BaseModel):
    message: str
