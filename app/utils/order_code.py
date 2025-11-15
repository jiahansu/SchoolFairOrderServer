


def generate_order_code(order_id: int) -> str:
    """Generate an order code like ORD-YYYYMMDD-0001 based on the order id."""

    #today_str = datetime.now(datetime.t).strftime("%Y%m%d")
    return f"ORD-{order_id:04d}"
