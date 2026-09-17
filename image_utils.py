"""Shared image validation used by both the local /upload endpoint and the
Google Drive sync — keeps the two in sync so a fix here fixes both paths."""

import io

import pillow_heif
from PIL import Image, UnidentifiedImageError

pillow_heif.register_heif_opener()

# Chromium (what the kiosk runs) can't render HEIC/HEIF at all, so anything
# in that format gets converted to JPEG before it's ever written to disk.
HEIF_FORMATS = {"HEIF", "HEIC"}


def normalize_image(data: bytes) -> tuple[bytes, bool]:
    """Validates image bytes, converting HEIC/HEIF to JPEG since browsers
    can't display it. Returns (bytes_to_store, was_converted).
    Raises ValueError if the data isn't a real image."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("not a valid image") from exc

    if img.format in HEIF_FORMATS:
        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=90)
        return buffer.getvalue(), True

    return data, False
