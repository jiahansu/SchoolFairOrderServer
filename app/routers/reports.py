from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, OrderStatus
from ..utils.excel import generate_orders_excel

router = APIRouter()


@router.get("/reports/orders.xlsx")
async def download_orders_report(
    status_filter: Optional[OrderStatus] = Query(OrderStatus.COMPLETED, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(Order).order_by(Order.created_at.asc())
    if status_filter is not None:
        query = query.filter(Order.status == status_filter.value)

    orders = query.all()

    output = generate_orders_excel(orders)

    filename = "orders_report.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
