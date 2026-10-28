"""What the phone app's 読む and 名詞 views show, kept free of Flet so it can be tested.

The views only draw; which fields and days have photos, which overlay belongs
to which photo, how an observation line is split for display, and how a photo
is shrunk for a phone screen are decided here.
"""

from __future__ import annotations

import io
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps

from .inbox import AROUND, DATED, photo_place

PHOTO_SUFFIXES = {".jpg", ".jpeg"}
OVERLAY = re.compile(r"^(?P<day>\d{4}-\d{2}-\d{2})-overlay-(?P<n>\d+)\.jpg$")
CONF = re.compile(r"\s*\[(?P<conf>[0-9.]+)\]\s*$")

KEY_LABELS = {
    "overall": "畑全体",
    "dominant": "優勢な草",
    "crops": "野菜",
    "acidity": "酸度",
    "fertility": "肥沃さ",
    "dryness": "乾き",
    "leaf_colour": "葉の色",
    "weed_height": "草の高さ",
    "soil": "土",
    "animal": "動物",
    "other": "その他",
    # the neighbourhood (around.py)
    "land_use": "土地の使われ方",
    "neighbours": "近所の様子",
    "water": "水",
    "seed_source": "種の出どころ",
    "animals": "動物",
    "history": "昔の使われ方",
}
AROUND_LABEL = "近所（畑のまわり）"


def place_label(name: str) -> str:
    return AROUND_LABEL if name == AROUND else name


def day_photos(photos_root: Path, field: str, day: str) -> list[Path]:
    """The photos filed for one field and day, in shooting order (names start with HHMMSS)."""
    d = photos_root / field / day
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in PHOTO_SUFFIXES)


def photo_days(photos_root: Path, field: str) -> list[str]:
    """Days of a field that have photos, newest first."""
    d = photos_root / field
    if not d.is_dir():
        return []
    days = [p.name for p in d.iterdir() if p.is_dir() and DATED.match(p.name) and day_photos(photos_root, field, p.name)]
    return sorted(days, reverse=True)


def photo_fields(photos_root: Path) -> list[str]:
    """Fields that have at least one day with photos, most recently used first."""
    if not photos_root.is_dir():
        return []
    fields = [d for d in photos_root.iterdir() if d.is_dir() and photo_place(d.name) and photo_days(photos_root, d.name)]
    return [d.name for d in sorted(fields, key=lambda d: d.stat().st_mtime, reverse=True)]


def concept_fields(records_root: Path) -> list[str]:
    """Fields that have a SAM concept list."""
    d = records_root / "_concepts"
    return sorted(p.stem for p in d.glob("*.md")) if d.is_dir() else []


def overlay_paths(records_root: Path, field: str, day: str) -> list[Path]:
    """records/<field>/<day>-overlay-<n>.jpg in photo order (n = 1, 2, … 10 sorts numerically)."""
    d = records_root / field
    if not d.is_dir():
        return []
    found = []
    for p in d.iterdir():
        m = OVERLAY.match(p.name)
        if m and m["day"] == day:
            found.append((int(m["n"]), p))
    return [p for _, p in sorted(found)]


def split_conf(text: str) -> tuple[str, str | None]:
    """'Lush, even. [0.8]' -> ('Lush, even.', '0.8')."""
    m = CONF.search(text)
    return (text[: m.start()], m["conf"]) if m else (text, None)


def key_label(key: str) -> str:
    return KEY_LABELS.get(key, key)


def last_label(last: str) -> str:
    """A concept's last SAM result, in Japanese: '2026-10-28 no match' -> '2026-10-28 見つからず'."""
    if last in ("", "-"):
        return "まだ使っていない"
    return last.replace("no match", "見つからず").replace("objects", "個")


@lru_cache(maxsize=64)
def _shrunk(path: str, mtime: float, max_side: int) -> bytes:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        return buf.getvalue()


def shrunk_jpeg(path: Path, max_side: int) -> bytes:
    """The photo as JPEG bytes no longer than max_side, upright. A phone photo is
    several MB; the browser gets a thumbnail, and the big one only when asked."""
    return _shrunk(str(path), path.stat().st_mtime, max_side)
