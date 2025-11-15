from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MenuItem
from ..schemas import MenuItemOut, Message
from ..utils.files import delete_file_if_exists, save_image_upload


router = APIRouter()

MEDIA_ROOT = "media"
MEDIA_SUBDIR = "uploads"
MEDIA_URL_PREFIX = "/media/"


def build_photo_url(photo_path: Optional[str]) -> Optional[str]:
    if not photo_path:
        return None
    return f"{MEDIA_URL_PREFIX}{photo_path}"


@router.post("/menu", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    name: str = Form(...),
    unit_price: Decimal = Form(...),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Create a new menu item, optionally with an uploaded photo."""

    photo_path: Optional[str] = None
    if photo is not None:
        photo_path = save_image_upload(photo, media_root=MEDIA_ROOT, subdir=MEDIA_SUBDIR)

    item = MenuItem(name=name, unit_price=unit_price, photo_path=photo_path)
    db.add(item)
    db.commit()
    db.refresh(item)

    return MenuItemOut(
        id=item.id,
        name=item.name,
        unit_price=item.unit_price,
        is_active=item.is_active,
        photo_url=build_photo_url(item.photo_path),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/menu", response_model=List[MenuItemOut])
async def list_menu_items(
    request: Request,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List menu items, optionally filtering by active flag (default: only active)."""

    query = db.query(MenuItem)
    if active is not None:
        query = query.filter(MenuItem.is_active == active)
    items = query.order_by(MenuItem.name).all()

    base_url = str(request.base_url).rstrip("/")
    media_prefix = MEDIA_URL_PREFIX.strip("/")

    return [
        MenuItemOut(
            id=item.id,
            name=item.name,
            unit_price=item.unit_price,
            is_active=item.is_active,
            photo_url=f"{base_url}/{media_prefix}/{item.photo_path}" if item.photo_path else None,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in items
    ]


@router.put("/menu/{menu_id}", response_model=MenuItemOut)
async def update_menu_item(
    menu_id: int,
    name: Optional[str] = Form(None),
    unit_price: Optional[Decimal] = Form(None),
    is_active: Optional[bool] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Update a menu item. Supports updating fields and replacing the photo."""

    item: Optional[MenuItem] = db.query(MenuItem).filter(MenuItem.id == menu_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    if name is not None:
        item.name = name
    if unit_price is not None:
        item.unit_price = unit_price
    if is_active is not None:
        item.is_active = is_active

    if photo is not None:
        # Delete old photo if exists
        delete_file_if_exists(item.photo_path, media_root=MEDIA_ROOT)
        item.photo_path = save_image_upload(photo, media_root=MEDIA_ROOT, subdir=MEDIA_SUBDIR)

    db.add(item)
    db.commit()
    db.refresh(item)

    return MenuItemOut(
        id=item.id,
        name=item.name,
        unit_price=item.unit_price,
        is_active=item.is_active,
        photo_url=build_photo_url(item.photo_path),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/menu/{menu_id}", response_model=Message)
async def delete_menu_item(
    menu_id: int,
    db: Session = Depends(get_db),
):
    """hard-delete a menu item and its photo."""

    item: Optional[MenuItem] = db.query(MenuItem).filter(MenuItem.id == menu_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")

    delete_file_if_exists(item.photo_path, media_root=MEDIA_ROOT)
    db.delete(item)
    db.commit()

    return Message(message="Menu item deleted")
