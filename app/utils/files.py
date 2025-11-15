import os
import shutil
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_image_upload(
    upload: UploadFile, media_root: str = "media", subdir: str = "uploads"
) -> str:
    """Save an uploaded image to the filesystem.

    Returns a relative path (e.g. "uploads/<filename>") that can be
    concatenated with the media base URL ("/media/").
    """

    if upload.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image type. Only JPEG and PNG are allowed.",
        )

    ext = os.path.splitext(upload.filename or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png"}:
        # If extension is missing but content-type is ok, default to .jpg
        if upload.content_type == "image/png":
            ext = ".png"
        else:
            ext = ".jpg"

    filename = f"{uuid.uuid4().hex}{ext}"
    relative_dir = subdir.strip("/")
    full_dir = os.path.join(media_root, relative_dir)
    ensure_directory(full_dir)

    full_path = os.path.join(full_dir, filename)

    with open(full_path, "wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    # Return path relative to media root
    return f"{relative_dir}/{filename}"


def delete_file_if_exists(path: Optional[str], media_root: str = "media") -> None:
    if not path:
        return
    full_path = os.path.join(media_root, path)
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
    except OSError:
        # We don't fail the whole request if file deletion fails
        pass
