"""What the phone app's 読む and 名詞 views show, kept free of Flet so it can be tested.

The views only draw; which fields and days have photos, which overlay belongs
to which photo, how an observation line is split for display, and how a photo
is shrunk for a phone screen are decided here.
"""

from __future__ import annotations

import io
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
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


# ---- the walk (WP18 item 3) ----------------------------------------------
# The day's photos as a strip in walk order, each GPS point drawn on the
# parcel outline (or the walk's own extent) the way walk.py places them.

Point = tuple[float, float]


@dataclass
class WalkMap:
    kind: str  # "parcel": the outline is the farm parcel; "walk": the walk's extent; "none": no GPS
    rings: list[list[Point]]  # the parcel outline(s) in canvas pixels, x right, y down
    points: list[Point | None]  # one per photo in walk order, in canvas pixels; None without GPS
    n_gps: int


def walk_map(found: list[dict], records_root: Path, width: float, height: float, pad: float = 14) -> WalkMap:
    """Where to draw each photo and the parcel on a width × height canvas: the frame walk.frame
    chooses (the parcel holding at least half the points, else the walk's extent, widened to
    show the parcel when there is one), scaled in metres so the shape is true, fitted with
    `pad` pixels around."""
    from .walk import EARTH_M_PER_DEG, frame
    gps = [(e["lon"], e["lat"]) for e in found if e.get("lat") is not None and e.get("lon") is not None]
    fr = frame(gps, records_root)
    if not fr:
        return WalkMap("none", [], [None] * len(found), 0)
    (w0, s0, e0, n0), kind, ring = fr
    rings = [[(x, y) for x, y in ring]] if ring else []
    for r in rings:  # the walk's frame grows to show the parcel it missed
        w0, e0 = min(w0, min(x for x, _ in r)), max(e0, max(x for x, _ in r))
        s0, n0 = min(s0, min(y for _, y in r)), max(n0, max(y for _, y in r))
    m_lon = EARTH_M_PER_DEG * math.cos(math.radians((s0 + n0) / 2))
    span_x, span_y = max((e0 - w0) * m_lon, 1.0), max((n0 - s0) * EARTH_M_PER_DEG, 1.0)
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad) / span_y)
    ox, oy = (width - span_x * scale) / 2, (height - span_y * scale) / 2

    def px(lon: float, lat: float) -> Point:
        return (round(ox + (lon - w0) * m_lon * scale, 1), round(oy + (n0 - lat) * EARTH_M_PER_DEG * scale, 1))

    return WalkMap(kind, [[px(x, y) for x, y in r] for r in rings],
                   [px(e["lon"], e["lat"]) if e.get("lat") is not None and e.get("lon") is not None else None for e in found],
                   len(gps))


@dataclass
class StripItem:
    n: int  # 1-based place in the walk
    photo: Path
    overlay: Path | None  # what SAM drew on it, once the day is read
    label: str  # "3 of 42, 10:21, NW corner, facing W" (walk.labels)
    entry: dict


def strip(root: Path, field: str, day: str) -> list[StripItem]:
    """The day's photos in walk order with their overlays and labels; empty when there are none."""
    from .walk import entries, labels
    found = entries(root, field, day)
    if not found:
        return []
    records = root / "records"
    overlays = overlay_paths(records, field, day)
    names = labels(found, records)
    d = root / "photos" / field / day
    return [StripItem(i + 1, d / e["file"], overlays[i] if i < len(overlays) else None, names.get(e["file"], ""), e)
            for i, e in enumerate(found)]


# ---- the land and the baseline (WP18 item 4) ------------------------------
# records/site.md and records/lookup.md line by line (docs/records.md §4, §5): each
# line keeps its status and the source after its em dash, so data, the farmer's
# words and readings never look alike on the screen.

STATUS = ("data", "record", "hypothesis", "supported", "refuted", "reference")
LAND_LINE = re.compile(r"^- `(?P<status>[a-z]+)` (?P<rest>.+)$")
CHECK_TAIL = re.compile(r"\bCheck(?: \([^)]*\))?:\s*")
LINK = re.compile(r"https?://[^\s,;）)]+")
FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


@dataclass
class LandLine:
    status: str  # one of STATUS, or "" for the file's own words that are no claim ("not reached on ...")
    text: str  # what is claimed
    source: str  # who or what says so: everything after the first em dash but the check
    check: str  # a hypothesis's "Check: ...", as the file words it
    raw: str  # the line without its marker, as expect.md copies it


@dataclass
class LandSection:
    heading: str
    lines: list[LandLine]


@dataclass
class LandPage:
    name: str  # "site.md"
    front: dict
    sections: list[LandSection]
    text: str  # the whole file, for anyone who wants to see it as it is


def land_line(line: str) -> LandLine:
    """One line of site.md or lookup.md. A line that has no status is kept as it stands."""
    m = LAND_LINE.match(line)
    if not m:
        return LandLine("", line.removeprefix("- ").strip(), "", "", "")
    text, _, tail = m["rest"].partition(" — ")
    c = CHECK_TAIL.search(tail)
    return LandLine(m["status"], text.strip(), (tail[: c.start()] if c else tail).strip(),
                    tail[c.end():].strip() if c else "", m["rest"].strip())


def land_page(records_root: Path, name: str) -> LandPage | None:
    """A page of the land by section; None when the file is not there. What stands before the
    first section (the legend of the statuses) is the format's, not the farm's."""
    p = records_root / name
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    m = FRONT.match(text)
    sections: list[LandSection] = []
    for line in (text[m.end():] if m else text).splitlines():
        if line.startswith("## "):
            sections.append(LandSection(line[3:].strip(), []))
        elif sections and line.strip():
            sections[-1].lines.append(land_line(line))
    return LandPage(name, (yaml.safe_load(m[1]) or {}) if m else {}, sections, text)


def status_counts(pages: list[LandPage]) -> dict[str, int]:
    """How many lines of each status the pages hold, in the order of STATUS."""
    found = [line.status for p in pages for s in p.sections for line in s.lines]
    return {k: found.count(k) for k in STATUS if k in found}


def link_parts(text: str) -> list[tuple[str, str | None]]:
    """A source split into plain text and links; a tile template ({z}/{x}/{y}) is no address to open."""
    out, at = [], 0
    for m in LINK.finditer(text):
        url = m[0].rstrip(".:")  # the sentence's full stop is not part of the address
        if "{" in url:
            continue
        if m.start() > at:
            out.append((text[at:m.start()], None))
        out.append((url, url))
        at = m.start() + len(url)
    if at < len(text):
        out.append((text[at:], None))
    return out


def _flat(text: str) -> str:
    return " ".join(str(text).split())


@dataclass
class HypothesisCheck:
    field: str
    id: str  # "h3" in that field's expect.md
    visible: bool  # False: expect.md says no photo can show it
    by_day: list[tuple[str, Observation]]  # the day's check line, oldest first


def hypothesis_checks(records_root: Path) -> dict[str, list[HypothesisCheck]]:
    """A hypothesis line's words -> what each field's photos said of it day by day. The numbers
    h1, h2 ... are those of the field's expect.md, joined by the words of the line, so a line
    written after expect.md has no entry rather than another hypothesis's answers."""
    from . import check, timeline
    out: dict[str, list[HypothesisCheck]] = {}
    d = records_root / check.CHECKS
    for field in sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []:
        got = check.load(records_root, field)
        if not got:
            continue
        lines = {o.key: o for o in got[1]}
        _, rows = timeline.checks_rows(records_root, field, timeline.days_of(records_root, field))
        cells = {h: c for h, _, c in rows}
        for h, words in (got[0].get("hypotheses") or {}).items():
            m = check.EXPECT_LINE.match(lines[h].text) if h in lines else None
            out.setdefault(_flat(words), []).append(HypothesisCheck(
                field, h, bool(m and m["visible"] == "yes"), sorted(cells.get(h, {}).items())))
    return out


def checks_of(found: dict[str, list[HypothesisCheck]], line: LandLine) -> list[HypothesisCheck]:
    return found.get(_flat(line.raw), [])


def answer_label(o: Observation, w: Words = Words("ja")) -> str:
    """A check line's answer on screen with the farmer's mark: 'agrees: ...' -> '合う ✓'."""
    answer = o.text.split(":", 1)[0].strip()
    key = "check." + answer.replace(" ", "_")
    return (w(key) if w.has(key) else answer) + {"right": " ✓", "wrong": " ✗"}.get(o.verdict, "")


def check_fields(records_root: Path) -> list[str]:
    """The fields that have expectations or a day's checks: the ones a hypotheses table can be drawn for."""
    from . import check, timeline
    found = set()
    d = records_root / check.CHECKS
    if d.is_dir():
        found |= {p.name for p in d.iterdir() if p.is_dir()}
    if records_root.is_dir():
        for p in records_root.iterdir():
            if p.is_dir() and not p.name.startswith("_") and timeline.checks_rows(records_root, p.name, timeline.days_of(records_root, p.name))[0]:
                found.add(p.name)
    return sorted(found)


def checks_by(records_root: Path, field: str, days: list[str], w: Words = Words("ja")) -> str:
    """Who checked each day's photos, for the head of the hypotheses table: the cells are readings."""
    by = []
    for d in days:
        p = Record.path_for(records_root, field, d)
        by.append(f"{short_day(d)} {Record.load(records_root, field, d).checks_model or 'none'}" if p.exists() else short_day(d))
    return w("land.table_by", list=", ".join(by))


def short_day(day: str) -> str:
    """'2026-11-02' -> '11-02', for a column head."""
    return day[5:] if DATED.match(day) else day


# ---- who reads, in which language (WP18 item 5) ----------------------------

def reader_line(w: Words, device: str | None = None) -> str:
    """The reader by name and the language its reading will be written in, from the settings:
    'Next reading by muse-spark-1.3 (Muse Spark (api.meta.ai)), written in English'."""
    from . import llm
    code = llm.language(device)
    lang = llm.language_label(code) + ("" if llm.language_setting() != llm.AUTO else " " + w("reader.auto_lang"))
    return w("reader.next", name=llm.reader_name(), kind=w("reader." + llm.reader()), lang=lang)


# ---- in the field (WP18 item 6) ---------------------------------------------

def lan_addresses() -> list[str]:
    """This PC's addresses a phone can reach: the one the default route leaves by (no packet is
    sent), then any others of the host name; loopback is no use to a phone."""
    import socket
    found: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # TEST-NET-1: connect() on UDP only picks the route
            found.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        found += [a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    return [a for a in dict.fromkeys(found) if not a.startswith("127.")]


def lan_urls(port: int, addresses: list[str] | None = None) -> list[str]:
    return [f"http://{a}:{port}/" for a in (lan_addresses() if addresses is None else addresses)]


def qr_text(url: str) -> str | None:
    """The address as a QR code in text, for the PC's terminal; None when qrcode is not installed
    (it comes with flet[all] through flet-cli, not as a dependency of its own)."""
    try:
        import qrcode
    except ImportError:
        return None
    q = qrcode.QRCode(border=2)
    q.add_data(url)
    q.make(fit=True)
    out = io.StringIO()
    q.print_ascii(out=out, invert=True)
    return out.getvalue()


# ---- honest state (WP18 item 7) ---------------------------------------------

VOICE_FILE = re.compile(r"^\d{6}-voice(?:-\d+)?\.[a-z0-9]+$", re.I)


def voice_files(photos_root: Path, field: str, day: str) -> list[Path]:
    d = photos_root / field / day
    return sorted(p for p in d.iterdir() if VOICE_FILE.match(p.name)) if d.is_dir() else []


def day_state(root: Path, field: str, day: str, rec: Record | None, w: Words = Words("ja")) -> list[str]:
    """What the day's screen cannot show, said plainly: no reading yet, SAM found nothing for
    the prompts it was given, a recording that was never written down, a reading with no
    lines, hypotheses not checked on this day though expect.md asks for it."""
    from . import check
    out: list[str] = []
    if rec is None:
        out.append(w("state.no_reading"))
    else:
        if rec.photos and not rec.observations:
            out.append(w("state.no_lines"))
        if rec.photos and not rec.coverage:
            out.append(w("state.no_sam"))
        elif rec.coverage and not any(v > 0 for v in rec.coverage.values()):
            out.append(w("state.sam_nothing", prompts=", ".join(rec.coverage)))
        if rec.photos and not rec.checks and check.path_for(root / "records", field).exists():
            out.append(w("state.no_checks"))
    note = rec.farmer_note if rec else ""
    for v in voice_files(root / "photos", field, day):
        if v.name not in note:
            out.append(w("state.voice_not_heard", name=v.name))
    return out


# ---- the video from the app (WP18 item 9) ---------------------------------------

FRAME = (1280, 720)
FRAME_BG = (18, 20, 24)  # the dark screen's background, so a narrow page sits in it unnoticed


def frame_png(png: bytes, size: tuple[int, int] = FRAME) -> bytes:
    """A screenshot of any size as a frame of exactly `size`: scaled to fit, never cropped,
    centred on the dark background."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    scale = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    out = Image.new("RGB", size, FRAME_BG)
    out.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def save_frame(png: bytes, folder: Path, view: str) -> Path:
    """<folder>/<view>-<YYYYMMDD-HHMMSS>.png, 1280x720; a second capture in the same second gets -2."""
    from datetime import datetime
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{view}-{datetime.now():%Y%m%d-%H%M%S}"
    path, n = folder / f"{stem}.png", 1
    while path.exists():
        n += 1
        path = folder / f"{stem}-{n}.png"
    path.write_bytes(frame_png(png))
    return path


# ---- the command line's work from the app (init, note, expect, propose, timeline) ---------------

def init_site(records_root: Path, place: str, country: str, lat: str | float, lon: str | float,
              climate: str = "", method: str = "") -> Path:
    """`fieldnotes init` from the app: a new farm's site.md. Never over an existing one."""
    from . import site
    path = records_root / site.FILE
    if path.exists():
        raise FileExistsError(f"{path} is already there")
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        raise ValueError("latitude and longitude are numbers (34.08, 134.44)") from None
    country = (country or "").strip()
    if not place.strip() or len(country) != 2 or not country.isalpha() or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("a place, a two-letter country code and a latitude and longitude on the earth are needed")
    path.parent.mkdir(parents=True, exist_ok=True)
    args = (place.strip(), country, lat, lon, climate.strip())
    path.write_text(site.template(*args, method.strip()) if method.strip() else site.template(*args), encoding="utf-8")
    return path


def add_note(records_root: Path, text: str, section: str, day, source: str = "") -> tuple[Path, str]:
    """`fieldnotes note` from the app: the farmer's words as a `record` line (or, with a source,
    a document's statement as `data`) at the end of a section of site.md."""
    from . import note
    if not text.strip():
        raise ValueError("nothing to note")
    line = note.line(" ".join(text.split()), source.strip() or None, day)
    return note.add(records_root, section, [line]), line


def latest_record(root: Path, field: str) -> Record | None:
    from . import pipeline
    return pipeline.latest_record(field, root, None)


def record_fields(root: Path) -> list[str]:
    """The fields with photos or records, most recently used first (as Send lists them)."""
    from .inbox import list_fields
    return list_fields(root / "photos", root / "records")


def file_front(path: Path) -> tuple[str, dict]:
    """A Markdown file's text and its front matter (model, date ...), {} when it has none."""
    text = path.read_text(encoding="utf-8")
    m = FRONT.match(text)
    front = yaml.safe_load(m[1]) if m else None
    return text, front if isinstance(front, dict) else {}
