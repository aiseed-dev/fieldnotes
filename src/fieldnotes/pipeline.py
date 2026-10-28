"""One observation, end to end: photos -> weather -> SAM -> reading -> record.

    run_observation(field, day)   the eight steps of docs/implementation.md
    mark(field, day, key, verdict, reason)   the farmer's verdict on one line
    merge_rerun(new, old)         what a re-run keeps of the farmer's work
    compare_latest(day)           rank the fields on the barometers

Photos are filed under photos/<field>/<day>/ by inbox.py. Everything the run
writes is plain text under records/ (plus one overlay JPEG per photo), so a
farmer can read and correct it without this code.

Running the same field and day again is normal (the farmer may run it twice),
so the AI lines are replaced but the farmer's verdicts and note are not lost.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

from . import around, concepts, describe, segment, weather
from .inbox import AROUND, DATED, valid_field
from .llm import Backend
from .plants import species_in
from .records import Observation, Record, previous_records

ROOT = Path(os.environ.get("FIELDNOTES_ROOT", ".")).resolve()
PHOTO_SUFFIXES = {".jpg", ".jpeg"}
PREVIOUS = 3  # earlier observations given to the model with today's
VERDICTS = ("right", "wrong")
CONF_TAIL = re.compile(r"\s*\[\d+(?:\.\d+)?\]$")
OVERLAY = re.compile(r"-overlay-(\d+)\.jpg$")

Progress = Callable[[str], None]


def _iso(day: date | str) -> str:
    return day if isinstance(day, str) else day.isoformat()


def _check_field(field: str) -> None:
    if not (valid_field(field) or field in (describe.COMPARE, AROUND)):
        raise ValueError(f"bad field name {field!r}")


# ---- finding things -----------------------------------------------------

def photos_for(field: str, day: date | str, root: Path = ROOT) -> list[str]:
    """Photo paths relative to root, sorted (file names start with the time)."""
    d = root / "photos" / field / _iso(day)
    if not d.is_dir():
        return []
    return [p.relative_to(root).as_posix() for p in sorted(d.iterdir()) if p.suffix.lower() in PHOTO_SUFFIXES]


def overlay_paths(field: str, day: date | str, root: Path = ROOT) -> list[Path]:
    """The SAM overlays of one observation, in photo order."""
    d = root / "records" / field
    found = [(int(m.group(1)), p) for p in d.glob(f"{_iso(day)}-overlay-*.jpg") if (m := OVERLAY.search(p.name))]
    return [p for _, p in sorted(found)]


def record_dates(field: str, root: Path = ROOT) -> list[str]:
    d = root / "records" / field
    return sorted(p.stem for p in d.glob("*.md") if DATED.match(p.name)) if d.is_dir() else []


def latest_record(field: str, root: Path = ROOT, upto: date | str | None = None) -> Record | None:
    """The newest record of `field`, not later than `upto` if given."""
    dates = [x for x in record_dates(field, root) if upto is None or x <= _iso(upto)]
    return Record.load(root / "records", field, dates[-1]) if dates else None


# ---- the farmer's work survives a re-run --------------------------------

def _same(a: Observation, b: Observation) -> bool:
    """Same key and same words; the confidence figure alone does not make a new reading."""
    return a.key == b.key and CONF_TAIL.sub("", a.text) == CONF_TAIL.sub("", b.text)


def merge_rerun(new: Record, old: Record) -> Record:
    """Put the farmer's work in `old` into the freshly read `new`.

    * a new line with the same key and text as a marked old line takes its
      verdict and reason;
    * a marked old line whose text changed is kept, with its verdict, under
      `earlier` (the "## Earlier AI lines" section), so the mark is never lost;
    * unmarked old lines are simply replaced;
    * the farmer note stays.
    """
    taken: set[int] = set()
    for o in new.observations:
        prior = next((p for p in old.observations if p.verdict and id(p) not in taken and _same(p, o)), None)
        if prior:
            taken.add(id(prior))
            o.verdict, o.reason = prior.verdict, prior.reason
    earlier = list(old.earlier)
    for p in old.observations:
        if p.verdict and id(p) not in taken and not any(
                _same(p, e) and e.verdict == p.verdict for e in earlier):
            earlier.append(p)
    new.earlier = earlier
    new.farmer_note, new.note_model = old.farmer_note, old.note_model
    return new


def save_merged(rec: Record, records_root: Path) -> Path:
    """Save `rec`, merging with the file already there, if any."""
    if Record.path_for(records_root, rec.field, rec.date).exists():
        rec = merge_rerun(rec, Record.load(records_root, rec.field, rec.date))
    return rec.save(records_root)


# ---- the observation ----------------------------------------------------

def run_observation(field: str, day: date, root: Path = ROOT, backend: Backend | None = None, *,
                    progress: Progress | None = None) -> Record:
    """Read the photos of `field` on `day` and save records/<field>/<day>.md.

    `progress`, if given, is called with a short Japanese line before each
    step (the app shows it while the work runs in a thread).
    """
    _check_field(field)
    say = progress or (lambda _msg: None)
    records = root / "records"
    day_s = _iso(day)

    # 1. photos
    photos = photos_for(field, day_s, root)
    if not photos:
        raise FileNotFoundError(f"no photos in photos/{field}/{day_s}/")
    backend = backend or Backend.default()
    if field == AROUND:  # the neighbourhood: one reading of the photos, no SAM or weather
        say("近所の写真を読んでいます")
        save_merged(around.read_around(root, day_s, photos, backend), records)
        return Record.load(records, field, day_s)
    rec = Record(field=field, date=day_s, photos=photos)

    # 2. weather: a missing day (the archive lags a few days) must not stop the reading
    say("天気を調べています")
    try:
        rec.weather = weather.daily_weather(date.fromisoformat(day_s), records)
    except (KeyError, OSError, ValueError) as e:
        say(f"天気は取れませんでした（{e}）")

    # 3. previous
    previous = previous_records(records, field, day_s, n=PREVIOUS)

    # 4. SAM prompts for the plants that dominated before
    say("SAM に聞く名詞を用意しています")
    shared = concepts.SharedConcepts.load(root / concepts.SHARED)
    concepts.ensure(records, field, species_in([o for r in previous for o in r.observations]), backend, shared)

    # 5. segmentation, one overlay per photo
    def segment_and_overlay():
        say(f"SAM で {len(photos)} 枚を分けています")
        results = concepts.segment_field(rec, photo_root=root, records_root=records)
        for old in overlay_paths(field, day_s, root):
            old.unlink()  # a re-run with fewer photos must not leave stale overlays
        for n, result in enumerate(results, start=1):
            segment.save_overlay(result, records / field / f"{day_s}-overlay-{n}.jpg")

    asked = set(concepts.FieldConcepts.load(records, field).nouns())
    segment_and_overlay()

    # 6. reading
    say("Muse Spark が畑を読んでいます")
    describe.observe(rec, previous, photo_root=root, records_root=records, backend=backend)

    # 7. prompts for next time
    say("次回の SAM の名詞を用意しています")
    concepts.ensure(records, field, species_in(rec.observations), backend, shared)

    # On a field's first days SAM had little to look for (only the defaults);
    # when today's reading added prompts, run SAM again so today's record and
    # overlays already show the dominant plants.
    if set(concepts.FieldConcepts.load(records, field).nouns()) - asked:
        segment_and_overlay()

    # 8. save, keeping the farmer's verdicts and note from an earlier run of this day
    say("記録を保存しています")
    save_merged(rec, records)
    return Record.load(records, field, day_s)


def _find_line(rec: Record, key: str) -> Observation:
    """`key` is the line's key; `key#2` picks the second line with that key."""
    base, _, nth = key.partition("#")
    lines = [o for o in rec.observations if o.key == base]
    i = int(nth) - 1 if nth.isdigit() else 0
    if not 0 <= i < len(lines):
        raise KeyError(f"no line {key!r} in {rec.field} {rec.date}")
    return lines[i]


def mark(field: str, day: date | str, key: str, verdict: str | None, reason: str | None = None, *,
         root: Path = ROOT) -> Observation:
    """Set the farmer's verdict ("right" / "wrong", or None to clear it) and
    reason on one AI line of a record. Returns the changed line."""
    _check_field(field)
    if verdict not in (*VERDICTS, None):
        raise ValueError(f"verdict must be right or wrong, not {verdict!r}")
    records = root / "records"
    rec = Record.load(records, field, _iso(day))
    line = _find_line(rec, key)
    line.verdict = verdict
    # one line in the file: fold any line breaks in the reason
    line.reason = (" ".join(reason.split()) or None) if verdict and reason else None
    rec.save(records)
    return line


# ---- fields side by side ------------------------------------------------

def fields_with_records(root: Path = ROOT) -> list[str]:
    d = root / "records"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and valid_field(p.name) and record_dates(p.name, root)) \
        if d.is_dir() else []


def compare_latest(day: date | str, root: Path = ROOT, backend: Backend | None = None) -> Record:
    """Rank the fields on the barometers from the newest record of each (not
    later than `day`), saved as records/_compare/<date>.md."""
    records = root / "records"
    latest = [r for f in fields_with_records(root) if (r := latest_record(f, root, day))]
    if len(latest) < 2:
        raise ValueError("need records of at least two fields to compare")
    backend = backend or Backend.default()
    history = previous_records(records, describe.COMPARE, _iso(day), n=PREVIOUS)
    rec = describe.compare_fields(latest, root, records, backend, history)
    save_merged(rec, records)
    return Record.load(records, rec.field, rec.date)
