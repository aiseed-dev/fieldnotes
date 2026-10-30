"""File photos sent from a phone into photos/<field>/<date>/.

The phone app uploads whatever the camera gives (JPEG, or HEIC from an
iPhone). Each photo is dated by its own EXIF capture time when it has one,
else by the date the farmer chose, converted to JPEG if needed (EXIF kept),
and named <HHMMSS>-<original name>.jpg so photos of the same day sort by time
and never overwrite each other.

The farmer walks the field with the phone's location on, so most photos also
carry GPS. Each day's folder keeps photos/<field>/<date>/index.json, one entry
per photo in walk order (capture time):

    [{"file": "102133-IMG_0042.jpg", "time": "10:21:33", "lat": 34.08, "lon": 134.44,
      "facing": 271.5, "cover": {"leaf": 41.0, ...}}, ...]

lat, lon and facing (the compass direction the camera faced) are null when the
photo has none; cover is what SAM found in that photo (pipeline.py fills it).
"""

from __future__ import annotations

import json
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
GPS_IFD = 0x8825
INDEX = "index.json"


def valid_field(name: str) -> bool:
    """Field names become folder names: lower-case letters, digits and hyphens."""
    return bool(FIELD_NAME.match(name))


AROUND = "_around"  # photos of the neighbourhood, not of a field (around.py)


def photo_place(name: str) -> bool:
    """Where photos may be filed: a field, or the neighbourhood."""
    return valid_field(name) or name == AROUND


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


def _degrees(dms, ref) -> float | None:
    try:
        d, m, sec = (float(x) for x in dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    v = d + m / 60 + sec / 3600
    return round(-v if str(ref).strip().upper() in ("S", "W") else v, 7)


def located_at(img: Image.Image) -> tuple[float | None, float | None, float | None]:
    """(lat, lon, facing) from the photo's EXIF GPS; None for what it lacks."""
    gps = img.getexif().get_ifd(GPS_IFD)
    lat, lon = _degrees(gps.get(2), gps.get(1)), _degrees(gps.get(4), gps.get(3))
    if lat is None or lon is None or (lat == 0 and lon == 0):  # 0,0 is a phone with no fix
        lat = lon = None
    try:
        facing = round(float(gps[17]), 1) if 17 in gps else None
    except (TypeError, ValueError, ZeroDivisionError):
        facing = None
    return lat, lon, facing


def index_day(day_dir: Path) -> list[dict]:
    """(Re)write day_dir/index.json from the photos there, in walk order, keeping
    the cover already found for photos still present. Returns the entries."""
    path = day_dir / INDEX
    old = {e["file"]: e for e in json.loads(path.read_text(encoding="utf-8"))} if path.exists() else {}
    entries = []
    for p in sorted(day_dir.iterdir()):
        if p.suffix.lower() not in (".jpg", ".jpeg"):
            continue
        with Image.open(p) as img:
            when = taken_at(img)
            lat, lon, facing = located_at(img)
        e = {"file": p.name, "time": when.strftime("%H:%M:%S") if when else None,
             "lat": lat, "lon": lon, "facing": facing}
        if "cover" in old.get(p.name, {}):
            e["cover"] = old[p.name]["cover"]
        entries.append(e)
    # walk order: capture time; a photo without one keeps its place by name (the upload time)
    entries.sort(key=lambda e: (e["time"] or f"{e['file'][0:2]}:{e['file'][2:4]}:{e['file'][4:6]}", e["file"]))
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return entries


def file_photo(src: Path, field: str, chosen: date, photos_root: Path) -> Path:
    """Move one uploaded photo into place and return its new path."""
    if not photo_place(field):
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
    index_day(dest_dir)
    return dest
