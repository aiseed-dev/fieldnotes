"""File photos sent from a phone into photos/<field>/<date>/.

The phone app uploads whatever the camera gives (JPEG, or HEIC from an
iPhone). Each photo is dated by its own EXIF capture time when it has one,
else by the date the farmer chose, converted to JPEG if needed (EXIF kept),
and named <HHMMSS>-<original name>.jpg so photos of the same day sort by time
and never overwrite each other.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

FIELD_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
EXIF_IFD = 0x8769
DATETIME_ORIGINAL = 0x9003
DATETIME = 0x0132


def valid_field(name: str) -> bool:
    """Field names become folder names: lower-case letters, digits and hyphens."""
    return bool(FIELD_NAME.match(name))


DATED = re.compile(r"^\d{4}-\d{2}-\d{2}(\.md)?$")


def list_fields(photos_root: Path, records_root: Path) -> list[str]:
    """Fields that already have dated photos or records, most recently used
    first. Other folders under records/ (maps, weather cache) are not fields."""
    seen: dict[str, float] = {}
    for root in (photos_root, records_root):
        if root.exists():
            for d in root.iterdir():
                if d.is_dir() and valid_field(d.name) and any(DATED.match(x.name) for x in d.iterdir()):
                    seen[d.name] = max(seen.get(d.name, 0.0), d.stat().st_mtime)
    return sorted(seen, key=seen.get, reverse=True)


def taken_at(img: Image.Image) -> datetime | None:
    exif = img.getexif()
    raw = exif.get_ifd(EXIF_IFD).get(DATETIME_ORIGINAL) or exif.get(DATETIME)
    try:
        return datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S") if raw else None
    except ValueError:
        return None


def file_photo(src: Path, field: str, chosen: date, photos_root: Path) -> Path:
    """Move one uploaded photo into place and return its new path."""
    if not valid_field(field):
        raise ValueError(f"bad field name {field!r}")
    with Image.open(src) as img:
        when = taken_at(img)
        day = when.date() if when else chosen
        stamp = when.strftime("%H%M%S") if when else datetime.now().strftime("%H%M%S")
        dest_dir = photos_root / field / day.isoformat()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{stamp}-{Path(src.name).stem}.jpg"
        n = 1
        while dest.exists():
            n += 1
            dest = dest_dir / f"{stamp}-{Path(src.name).stem}-{n}.jpg"
        if img.format == "JPEG":
            src.replace(dest)
        else:
            exif = img.getexif()
            img.convert("RGB").save(dest, "JPEG", quality=92, exif=exif.tobytes() if exif else b"")
            src.unlink()
    return dest
