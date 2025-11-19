from collections import defaultdict
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem, Order, OrderItem, OrderStatus
from ..schemas import ItemStats, Message, OrderCreate, OrderOut, OrderStats
from ..utils.order_code import generate_order_code

router = APIRouter()


def serialize_order(order: Order) -> OrderOut:
    return OrderOut.from_orm(order)


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item")

    # Load menu items and validate
    menu_ids = {item.menu_item_id for item in payload.items}
    menu_items = (
        db.query(MenuItem)
        .filter(MenuItem.id.in_(menu_ids))
        .filter(MenuItem.is_active == True)  # noqa: E712
        .all()
    )
    menu_map = {m.id: m for m in menu_items}

    if len(menu_map) != len(menu_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Some menu items are invalid or inactive")

    order = Order(customer_name=payload.customer_name, status=OrderStatus.NEW.value, total_price=Decimal("0.00"), preorder=payload.preorder)
    db.add(order)
    db.flush()  # get order.id

    total_price = Decimal("0.00")

    for item in payload.items:
        menu = menu_map[item.menu_item_id]
        unit_price = Decimal(menu.unit_price)
        line_total = unit_price * item.quantity
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu.id,
            item_name=menu.name,
            unit_price=unit_price,
            quantity=item.quantity,
            line_total=line_total,
        )
        db.add(order_item)
        total_price += line_total

    order.total_price = total_price
    # Generate order code after getting ID
    order.order_code = generate_order_code(order.id)

    db.add(order)
    db.commit()
    db.refresh(order)

    return serialize_order(order)


@router.get("/orders", response_model=List[OrderOut])
async def list_orders(
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    preorder_filter: Optional[bool] = Query(None, alias="preorder"),
    db: Session = Depends(get_db),
):
    query = db.query(Order).order_by(Order.created_at.asc())
    if preorder_filter is not None:
        query = query.filter(Order.preorder == preorder_filter)
    if status_filter is not None:
        query = query.filter(Order.status == status_filter.value)
    

    orders = query.all()
    return [serialize_order(o) for o in orders]


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order: Optional[Order] = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != OrderStatus.NEW.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only NEW orders can be canceled")

    order.status = OrderStatus.CANCELED.value
    db.add(order)
    db.commit()
    db.refresh(order)

    return serialize_order(order)


@router.post("/orders/{order_id}/await", response_model=OrderOut)
async def await_order(order_id: int, db: Session = Depends(get_db)):
    order: Optional[Order] = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != OrderStatus.NEW.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only NEW orders can be awaiting")

    order.status = OrderStatus.AWAITING.value
    db.add(order)
    db.commit()
    db.refresh(order)

    return serialize_order(order)


@router.post("/orders/{order_id}/complete", response_model=OrderOut)
async def complete_order(order_id: int, db: Session = Depends(get_db)):
    order: Optional[Order] = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != OrderStatus.AWAITING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only AWAITING orders can be completed")

    order.status = OrderStatus.COMPLETED.value
    db.add(order)
    db.commit()
    db.refresh(order)

    return serialize_order(order)


@router.get("/orders/statuses", response_model=List[str])
async def list_order_statuses():
    return [status.value for status in OrderStatus]


@router.get("/orders/stats", response_model=OrderStats)
async def get_order_stats(
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    preorder_filter: Optional[bool] = Query(None, alias="preorder"),
    db: Session = Depends(get_db),
):
    query = db.query(Order)
    if status_filter is not None:
        query = query.filter(Order.status == status_filter.value)
    if preorder_filter is not None:
        query = query.filter(Order.preorder == preorder_filter)

    orders: List[Order] = query.all()

    total_orders = len(orders)
    total_amount = Decimal("0.00")

    item_map: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {"quantity": 0, "amount": Decimal("0.00")}
    )

    for order in orders:
        for item in order.items:
            total_amount += item.line_total
            agg = item_map[item.item_name]
            agg["quantity"] += item.quantity
            agg["amount"] += item.line_total

    items_stats: List[ItemStats] = [
        ItemStats(item_name=name, total_quantity=data["quantity"], total_amount=data["amount"])
        for name, data in item_map.items()
    ]

    return OrderStats(total_orders=total_orders, total_amount=total_amount, items=items_stats)


@router.delete("/orders", response_model=Message)
async def delete_all_orders(db: Session = Depends(get_db)):
    """Delete all orders and their associated order items."""
    orders: List[Order] = db.query(Order).all()
    deleted_count = len(orders)

    for order in orders:
        db.delete(order)

    db.commit()

    return Message(message=f"Deleted {deleted_count} orders")
