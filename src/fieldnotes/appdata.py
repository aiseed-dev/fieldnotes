"""What the phone app's 読む and 名詞 views show, kept free of Flet so it can be tested.

The views only draw; which fields and days have photos, which overlay belongs
to which photo, how an observation line is split for display, and how a photo
is shrunk for a phone screen are decided here.
"""

from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageOps

from .inbox import AROUND, DATED, photo_place
from .records import Observation, Record
from .ui import Words

PHOTO_SUFFIXES = {".jpg", ".jpeg"}
OVERLAY = re.compile(r"^(?P<day>\d{4}-\d{2}-\d{2})-overlay-(?P<n>\d+)\.jpg$")
CONF = re.compile(r"\s*\[(?P<conf>[0-9.]+)\]\s*$")

def place_label(name: str, w: Words = Words("ja")) -> str:
    return w("around") if name == AROUND else name


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


def key_label(key: str, w: Words = Words("ja")) -> str:
    """A record line's title on screen: 'dominant' -> '優勢な草' / 'Dominant plants'."""
    return w("key." + key) if w.has("key." + key) else key


def last_label(last: str, w: Words = Words("ja")) -> str:
    """A concept's last SAM result on screen: '2026-10-28 no match' -> '2026-10-28 見つからず'."""
    if last in ("", "-"):
        return w("last.never")
    return last.replace("no match", w("last.no_match")).replace("objects", w("last.objects"))


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


# ---- marking (WP18 item 1) -------------------------------------------------
# Every line a model wrote on a day is marked from one row; the references are
# the ones pipeline.mark understands (key, key#2 ...; work/seen for the voice
# lines, h3 for the checks).

@dataclass
class LineRef:
    group: str  # "ai" | "voice" | "checks"
    ref: str  # what pipeline.mark takes: "dominant", "zone#2", "work", "h3"
    line: Observation


def line_refs(rec: Record) -> list[LineRef]:
    """The day's markable lines in file order, each with its mark reference."""
    out = []
    for group, pool in (("ai", rec.observations), ("voice", rec.voice), ("checks", rec.checks)):
        seen: dict[str, int] = {}
        for o in pool:
            seen[o.key] = seen.get(o.key, 0) + 1
            out.append(LineRef(group, o.key if seen[o.key] == 1 else f"{o.key}#{seen[o.key]}", o))
    return out


def mark_count(rec: Record) -> tuple[int, int, int]:
    """(right, wrong, total) over every model line of the day: the AI's reading,
    the voice lines it sorted and the checks."""
    refs = line_refs(rec)
    return (sum(r.line.verdict == "right" for r in refs), sum(r.line.verdict == "wrong" for r in refs), len(refs))


def count_label(rec: Record, w: Words = Words("ja")) -> str:
    right, wrong, total = mark_count(rec)
    return w("read.count", right=right, wrong=wrong, total=total)


# ---- readings, not answers (WP18 item 2) ---------------------------------
# A model line is headed by its model and date and the sources the model was
# given; two readings of the same field and day (another farm folder next to
# this one, e.g. sample/ and sample-en/, or the lines a re-run replaced) stand
# side by side for the same key so the farmer marks both.

ALSO = "FIELDNOTES_ALSO"  # more farm folders whose readings stand beside this one's, os.pathsep-separated


@dataclass
class Reading:
    label: str  # where it is from: the folder's name, or "earlier" for the lines a re-run replaced
    root: Path | None  # the farm folder whose records/ holds it (None: not markable)
    record: Record
    refs: list[LineRef]


def sibling_roots(root: Path) -> list[Path]:
    """Farm folders beside `root` named <root>-<something> with a records/ folder (sample → sample-en),
    and those named in $FIELDNOTES_ALSO."""
    root = root.resolve()
    found = []
    if root.parent.is_dir():
        found += sorted(p for p in root.parent.iterdir()
                        if p.is_dir() and p != root and p.name.startswith(root.name + "-") and (p / "records").is_dir())
    for x in filter(None, os.environ.get(ALSO, "").split(os.pathsep)):
        p = Path(x).expanduser().resolve()
        if (p / "records").is_dir() and p != root and p not in found:
            found.append(p)
    return found


def readings(root: Path, field: str, day: str) -> list[Reading]:
    """The day's reading in this farm folder, the lines a re-run of it replaced, and the same
    field and day in the sibling folders; the first is the one the view is about."""
    out = []
    for r in [root] + sibling_roots(root):
        path = Record.path_for(r / "records", field, day)
        if not path.exists():
            continue
        try:
            rec = Record.load(r / "records", field, day)
        except Exception:  # noqa: BLE001 - a broken sibling must not hide the day
            continue
        out.append(Reading(r.resolve().name, r, rec, line_refs(rec)))
        if r == root and rec.earlier:
            out.append(Reading("earlier", None, rec, [LineRef("ai", o.key, o) for o in rec.earlier]))
    return out


def side_by_side(found: list[Reading]) -> list[tuple[str, str, list[LineRef | None]]]:
    """(group, ref, one LineRef or None per reading): the first reading's lines in its order,
    then any line only another reading has, so the same key stands in one row."""
    rows: dict[tuple[str, str], list[LineRef | None]] = {}
    for i, reading in enumerate(found):
        for ref in reading.refs:
            cells = rows.setdefault((ref.group, ref.ref), [None] * len(found))
            cells[i] = ref
    order = {"ai": 0, "voice": 1, "checks": 2}
    return [(g, r, cells) for (g, r), cells in sorted(rows.items(), key=lambda kv: order[kv[0][0]]) if any(cells)] \
        if len(found) > 1 else [(ref.group, ref.ref, [ref]) for ref in found[0].refs] if found else []


def model_of(rec: Record, group: str) -> str:
    return {"ai": rec.ai_model, "voice": rec.voice_model, "checks": rec.checks_model}[group] or "none"


def sources(rec: Record, records_root: Path, w: Words = Words("ja")) -> str:
    """What the reading model was given for this day, as the record shows it: the photos,
    SAM's cover numbers, the weather, the farm's site and lookup pages, and the earlier days
    with the farmer's corrections (pipeline.run_observation, describe.build_messages)."""
    from .records import previous_records
    parts = [w("src.photos", n=len(rec.photos))]
    if rec.coverage:
        parts.append(w("src.sam", n=len(rec.coverage)))
    if rec.weather:
        parts.append(w("src.weather"))
    pages = [name for name in ("site.md", "lookup.md", "surroundings.md") if (records_root / name).exists()]
    if pages:
        parts.append(", ".join(pages))
    try:
        earlier = previous_records(records_root, rec.field, rec.date, n=3)
    except Exception:  # noqa: BLE001 - a broken earlier record is not this day's problem
        earlier = []
    if earlier:
        wrong = sum(o.verdict == "wrong" for r in earlier for o in r.observations)
        parts.append(w("src.earlier", n=len(earlier), wrong=wrong))
    return w("src.given", list=", ".join(parts))
