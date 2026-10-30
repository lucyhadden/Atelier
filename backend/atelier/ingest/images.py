"""Fetching and storing images on disk."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import httpx
from PIL import Image

from ..config import get_settings

log = logging.getLogger(__name__)

# Claude's vision input is capped, and a 4000px pin costs tokens without
# telling us anything a 1600px one does not.
MAX_EDGE = 1600
JPEG_QUALITY = 88
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".heic"}


class ImageError(RuntimeError):
    pass


def _normalise(path: Path) -> None:
    """Downscale in place and strip to a format Claude accepts."""
    try:
        with Image.open(path) as img:
            img.load()
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            if max(img.size) > MAX_EDGE:
                img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            img.save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    except Exception as exc:
        raise ImageError(f"Could not process image {path.name}: {exc}") from exc


def store_from_url(url: str, *, prefix: str = "pin") -> str:
    """Download an image and return its filename inside the image dir."""
    digest = hashlib.sha256(url.encode()).hexdigest()[:20]
    filename = f"{prefix}_{digest}.jpg"
    dest = get_settings().image_dir / filename
    if dest.exists():
        return filename

    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
    except httpx.HTTPError as exc:
        raise ImageError(f"Could not download {url}: {exc}") from exc

    try:
        _normalise(dest)
    except ImageError:
        dest.unlink(missing_ok=True)
        raise
    return filename


def store_from_bytes(data: bytes, original_name: str, *, prefix: str = "upload") -> str:
    suffix = Path(original_name).suffix.lower()
    if suffix and suffix not in ALLOWED_SUFFIXES:
        raise ImageError(f"Unsupported image type {suffix!r}")
    digest = hashlib.sha256(data).hexdigest()[:20]
    filename = f"{prefix}_{digest}.jpg"
    dest = get_settings().image_dir / filename
    if not dest.exists():
        dest.write_bytes(data)
        try:
            _normalise(dest)
        except ImageError:
            dest.unlink(missing_ok=True)
            raise
    return filename


def store_from_path(src: Path, *, prefix: str = "local") -> str:
    if src.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ImageError(f"Unsupported image type {src.suffix!r}")
    return store_from_bytes(src.read_bytes(), src.name, prefix=prefix)
