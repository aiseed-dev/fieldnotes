"""One walk over a field: many photos, each with its time and place, read as one field.

The farmer walks each field on the same route every day and shoots 20-50
photos with the phone's location on; inbox.py keeps them in walk order in
photos/<field>/<date>/index.json. This module says where each photo was taken,
in words a model and a farmer both read ("NW corner", "middle", "S edge"):

* relative to the farm parcel (筆ポリゴン, records/lookup/parcel_jp.json) that
  holds at least half of the day's photo points;
* else relative to the walk's own extent;
* without GPS, by walk order only ("photo 3 of 42").

Each photo is labelled "3 of 42, 10:21, NW corner, facing W"; the reading and
the map use the same numbers and words.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .inbox import INDEX, index_day

MAX_IMAGES = 50  # Muse Spark, per request (dev.meta.ai, Image understanding, read 2026-10-30): more returns HTTP 400
SIDE = 1024  # long side of each photo sent with a walk; about 1,000 input tokens each
EARTH_M_PER_DEG = 111_320.0
ONE_SPOT_M = 3.0  # photo points closer than this (the phone's GPS error) are one spot
GRID = [["NW corner", "N edge", "NE corner"], ["W edge", "middle", "E edge"], ["SW corner", "S edge", "SE corner"]]
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

Box = tuple[float, float, float, float]  # west, south, east, north (degrees)


def day_dir(root: Path, field: str, day: str) -> Path:
    return root / "photos" / field / day


def entries(root: Path, field: str, day: str) -> list[dict]:
    """The day's index, rebuilt when photos were added or removed by hand."""
    d = day_dir(root, field, day)
    if not d.is_dir():
        return []
    path = d / INDEX
    files = {p.name for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg")}
    if path.exists():
        got = json.loads(path.read_text(encoding="utf-8"))
        if {e["file"] for e in got} == files:
            return got
    return index_day(d)


def save_cover(root: Path, field: str, day: str, cover: dict[str, dict[str, float]]) -> None:
    """Keep what SAM found in each photo (file name -> {noun: %}) in the day's index."""
    got = entries(root, field, day)
    for e in got:
        if e["file"] in cover:
            e["cover"] = cover[e["file"]]
    (day_dir(root, field, day) / INDEX).write_text(json.dumps(got, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")


def sample(items: list, k: int) -> list:
    """k items spread evenly along the walk (all of them when k covers it)."""
    if k >= len(items):
        return list(items)
    if k <= 0:
        return []
    if k == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (k - 1))] for i in range(k)]


# ---- where a photo was taken ----------------------------------------------

def _rings(geom: dict) -> list[list[list[float]]]:
    if geom.get("type") == "Polygon":
        return geom["coordinates"][:1]
    if geom.get("type") == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def parcels(records_root: Path) -> list[list[list[float]]]:
    """The outer rings of the parcel at the farm's point and its neighbours, as looked up."""
    p = records_root / "lookup" / "parcel_jp.json"
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    feats = [raw.get("parcel")] + list((raw.get("near") or {}).get("features") or [])
    return [r for f in feats if f and f.get("geometry") for r in _rings(f["geometry"])]


def inside(lon: float, lat: float, ring: list[list[float]]) -> bool:
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def _bounds(points: list[tuple[float, float]]) -> Box:
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def box(points: list[tuple[float, float]], records_root: Path) -> tuple[Box, str] | None:
    """The frame the positions are given in, and what it is ("parcel" or "walk"):
    the parcel holding at least half the points, else the points' own extent."""
    if not points:
        return None
    best = max(parcels(records_root), key=lambda r: sum(inside(x, y, r) for x, y in points), default=None)
    if best and 2 * sum(inside(x, y, best) for x, y in points) >= len(points):
        return _bounds([(x, y) for x, y in best]), "parcel"
    return _bounds(points), "walk"


def place(lon: float, lat: float, frame: Box) -> str:
    """Which ninth of the frame the point lies in; an axis shorter than a GPS error counts as the middle."""
    w, s, e, n = frame
    m_lon = EARTH_M_PER_DEG * math.cos(math.radians((s + n) / 2))

    def third(v, lo, hi, m_per_deg):
        if (hi - lo) * m_per_deg < ONE_SPOT_M:
            return 1
        f = (v - lo) / (hi - lo)
        return 0 if f < 1 / 3 else 2 if f > 2 / 3 else 1

    return GRID[2 - third(lat, s, n, EARTH_M_PER_DEG)][third(lon, w, e, m_lon)]


def facing(deg: float | None) -> str | None:
    return None if deg is None else COMPASS[round(deg % 360 / 45) % 8]


def labels(found: list[dict], records_root: Path) -> dict[str, str]:
    """File name -> "3 of 42, 10:21, NW corner, facing W", for the photos of one walk."""
    points = [(e["lon"], e["lat"]) for e in found if e.get("lat") is not None]
    frame = box(points, records_root)
    out = {}
    for i, e in enumerate(found, start=1):
        parts = [f"{i} of {len(found)}"]
        if e.get("time"):
            parts.append(e["time"][:5])
        if frame and e.get("lat") is not None:
            parts.append(place(e["lon"], e["lat"], frame[0]))
        if (f := facing(e.get("facing"))):
            parts.append(f"facing {f}")
        out[e["file"]] = ", ".join(parts)
    return out


def frame_note(found: list[dict], records_root: Path) -> str:
    """One sentence for the prompt: what the positions are relative to."""
    points = [(e["lon"], e["lat"]) for e in found if e.get("lat") is not None]
    frame = box(points, records_root)
    if not frame:
        return "The photos carry no location; they are numbered in the order the farmer walked."
    what = "the farm parcel (筆ポリゴン) the photos lie in" if frame[1] == "parcel" else "the area the walk covered"
    return (f"The photos are numbered in the order the farmer walked; {len(points)} of {len(found)} carry GPS, "
            f"and their positions (NW corner, middle, S edge ...) are relative to {what}.")
