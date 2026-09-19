from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_IMAGE_PIXELS = 60_000_000


def validate_image_content(path: Path) -> None:
    header = path.read_bytes()[:16]
    suffix = path.suffix.lower()
    valid = (
        (suffix in {".jpg", ".jpeg"} and header.startswith(b"\xff\xd8\xff"))
        or (suffix == ".png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
        or (suffix == ".webp" and header.startswith(b"RIFF") and header[8:12] == b"WEBP")
        or (suffix in {".heic", ".heif"} and header[4:8] == b"ftyp")
    )
    if not valid:
        raise ValueError(f"{path.name} does not contain a valid {suffix.lstrip('.').upper()} image.")
    if suffix not in {".heic", ".heif"}:
        try:
            with Image.open(path) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError(f"{path.name} exceeds the image dimension limit.")
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError(f"{path.name} contains invalid or corrupted image data.") from exc


def ordered_image_name(position: int, original_name: str, content_type: Optional[str]) -> str:
    suffix = ALLOWED_IMAGE_TYPES.get(content_type or "", Path(original_name).suffix.lower())
    if suffix == ".jpeg":
        suffix = ".jpg"
    if suffix not in ALLOWED_EXTENSIONS:
        suffix = ".jpg"
    return f"{position:03d}{suffix}"


def validate_image_batch(
    names: list[str],
    content_types: list[Optional[str]],
    min_images: int,
    max_images: int,
) -> None:
    count = len(names)
    if count < min_images or count > max_images:
        raise ValueError(f"Upload {min_images}-{max_images} images.")

    for name, content_type in zip(names, content_types):
        suffix = Path(name).suffix.lower()
        if content_type not in ALLOWED_IMAGE_TYPES and suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(f"{name} is not a supported image.")
