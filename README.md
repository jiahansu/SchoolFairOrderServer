# Fun Fair Order Management Server

A simple HTTP server for managing food orders at a fun fair, built with **FastAPI** and **SQLite** (single file database `database.db`).

Features:
- Manage menu items (create, update, list, soft-delete)
- Each menu item can have an uploaded photo stored on the filesystem
- Create orders with multiple items
- Cancel / complete orders with simple status rules
- List all orders and available statuses
- Get statistics per item (total quantity and amount)
- Download an Excel report of orders (with totals and per-item summary)

---

## 1. Requirements & Installation

1. Make sure you have **Python 3.10+** installed.
2. In the project root (this folder), install dependencies:

```bash
pip install -r requirements.txt
```

SQLite is used as the database backend. The database file will be created automatically as `database.db` in the project root on first run.

> Note: uploaded images will be stored under the `media/uploads/` directory. The `media` folder is already mounted as static files at `/media`.

---

## 2. Project Structure

```text
OrderServer/
├── requirements.txt
├── README.md
├── database.db            # created automatically on first run
├── media/                 # uploaded images (served at /media)
└── app/
    ├── __init__.py
    ├── main.py
    ├── database.py
    ├── models.py
    ├── schemas.py
    ├── routers/
    │   ├── __init__.py
    │   ├── menu.py
    │   ├── orders.py
    │   └── reports.py
    └── utils/
        ├── __init__.py (optional)
        ├── files.py
        ├── order_code.py
        └── excel.py
```

---

## 3. Running the Server

From the project root:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs will be available at:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Health check:

```bash
curl http://127.0.0.1:8000/health
```

---

## 4. Data Model Overview

### Menu Item
- `id`
- `name`
- `unit_price`
- `is_active`
- `photo_url` (derived from stored `photo_path`)
- `created_at`
- `updated_at`

### Order
- `id`
- `order_code` (e.g. `ORD-0001`)
- `customer_name`
- `status` (`NEW`, `COMPLETED`, `CANCELED`)
- `total_price`
- `created_at`
- `updated_at`
- `items[]` (list of order items)

### Order Item
- `id`
- `order_id`
- `menu_item_id` (nullable; keep snapshot even if menu is deleted)
- `item_name` (snapshot of menu item name at order time)
- `unit_price` (snapshot of price at order time)
- `quantity`
- `line_total`

---

## 5. API Summary

### 5.1 Menu APIs

#### Create Menu Item (with optional photo)

- **POST** `/menu`
- Content-Type: `multipart/form-data`

Form fields:
- `name` (string, required)
- `unit_price` (decimal string, required)
- `photo` (file, optional; JPEG/PNG)

Example:

```bash
curl -X POST "http://127.0.0.1:8000/menu" \
  -F "name=炸雞" \
  -F "unit_price=80" \
  -F "photo=@/path/to/photo.jpg;type=image/jpeg"
```

#### List Menu Items

- **GET** `/menu`
- Query parameters:
  - `active` (bool, optional, default: `true`)

```bash
curl "http://127.0.0.1:8000/menu?active=true"
```

#### Update Menu Item

- **PUT** `/menu/{menu_id}`
- Content-Type: `multipart/form-data`
- All fields are optional; only send what you want to update.

Form fields:
- `name` (string, optional)
- `unit_price` (decimal string, optional)
- `is_active` (bool, optional)
- `photo` (file, optional; JPEG/PNG, will replace old photo)

Example:

```bash
curl -X PUT "http://127.0.0.1:8000/menu/1" \
  -F "name=大炸雞" \
  -F "unit_price=90"
```

#### Soft-Delete (Deactivate) Menu Item

- **DELETE** `/menu/{menu_id}`

```bash
curl -X DELETE "http://127.0.0.1:8000/menu/1"
```

---

### 5.2 Order APIs

#### Create Order (multiple items supported)

- **POST** `/orders`
- Content-Type: `application/json`

Body example:

```json
{
  "customer_name": "王小明",
  "items": [
    { "menu_item_id": 1, "quantity": 2 },
    { "menu_item_id": 2, "quantity": 1 }
  ]
}
```

Curl example:

```bash
curl -X POST "http://127.0.0.1:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "王小明",
    "items": [
      { "menu_item_id": 1, "quantity": 2 },
      { "menu_item_id": 2, "quantity": 1 }
    ]
  }'
```

#### List Orders (with optional status filter)

- **GET** `/orders`
- Query parameters:
  - `status` = `NEW` | `COMPLETED` | `CANCELED` (optional)

Examples:

```bash
# All orders
curl "http://127.0.0.1:8000/orders"

# Only COMPLETED orders
curl "http://127.0.0.1:8000/orders?status=COMPLETED"
```

#### Cancel Order

- **POST** `/orders/{order_id}/cancel`
- Only orders with `status = NEW` can be canceled.

```bash
curl -X POST "http://127.0.0.1:8000/orders/1/cancel"
```

#### Complete Order

- **POST** `/orders/{order_id}/complete`
- Only orders with `status = NEW` can be completed.

```bash
curl -X POST "http://127.0.0.1:8000/orders/1/complete"
```

#### List Available Statuses

- **GET** `/orders/statuses`

```bash
curl "http://127.0.0.1:8000/orders/statuses"
```

---

### 5.3 Statistics API

#### Get Order Statistics

- **GET** `/orders/stats`
- Query parameters:
  - `status` = `NEW` | `COMPLETED` | `CANCELED` (optional)

Response example:

```json
{
  "total_orders": 10,
  "total_amount": 12345.0,
  "items": [
    {
      "item_name": "炸雞",
      "total_quantity": 20,
      "total_amount": 1600.0
    },
    {
      "item_name": "珍珠奶茶",
      "total_quantity": 15,
      "total_amount": 900.0
    }
  ]
}
```

Example request:

```bash
curl "http://127.0.0.1:8000/orders/stats?status=COMPLETED"
```

---

### 5.4 Excel Report

#### Download Orders Excel File

- **GET** `/reports/orders.xlsx`
- Query parameters:
  - `status` = `NEW` | `COMPLETED` | `CANCELED` | `ALL` (optional, default: `COMPLETED`).
    - Note: `ALL` is represented by omitting the parameter or by not filtering in code; default behavior here is `COMPLETED`.

Example:

```bash
curl -o orders_report.xlsx "http://127.0.0.1:8000/reports/orders.xlsx?status=COMPLETED"
```

The generated Excel file contains:
- One row per order item (order + item info)
- Overall total amount
- Per-item summary (total quantity & total amount)

---

## 6. Notes

- All money-related values use `DECIMAL(10,2)` in the database to avoid floating point precision issues.
- Deleting a menu item only deactivates it (`is_active = false`); existing orders keep their item name and price snapshot.
- Uploaded images are not removed when an order is deleted (orders are not currently deletable through the API).

---

## 7. Quick Start Flow

1. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Create a few menu items via `/docs` or using curl (with photos if needed).
3. Create an order with multiple items.
4. Complete or cancel the order.
5. Check statistics at `/orders/stats`.
6. Download the Excel report from `/reports/orders.xlsx`.

This should satisfy the fun fair order management use case: menu maintenance, order creation & lifecycle management, status listing, Excel export, and aggregated statistics per item.
