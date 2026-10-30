"""Check the farm's hypotheses against the photos: expectations first, then each day's photos.

records/site.md holds the hypotheses: claims about the farm's ground, water
and history, by the farmer or an AI, not yet checked. Public data settles some
(`lookup`); the rest are checked here, mainly from the plants, as site.md's
section "How a hypothesis is checked" asks. Two steps that never share a call,
so the expectation is written before any photo is seen and cannot be bent to fit:

1. `expect(field)`, text only. For each hypothesis line of site.md, in file
   order (h1, h2 ...): what photos of this field would show if it holds, what if
   it fails, and whether photos can show it at all (a flood 2000 years ago or
   water 4 m down cannot: kept, not checked). Saved as

       records/_checks/<field>/expect.md

   with the site.md lines it was written from in the front matter; the farmer
   marks each line right or wrong, or edits it. Run again when the hypotheses change.

2. `check_record(rec)`, called by observe when expect.md exists: the day's
   photos and the visible expectations (less those the farmer marked wrong)
   give one line per hypothesis in the record's "## Checks" section:

       - h3: agrees | disagrees | cannot tell: what the photos showed [conf]

   marked like any other line; a re-run of the day keeps the marks.

Day after day these lines are the record of each hypothesis (timeline.py puts
them side by side). Nothing here changes a hypothesis in site.md: the farmer does.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .describe import SITE_CHECK_HEADING, _body, _photo_parts, day_summary, site_background
from .llm import Backend, chat, conf, in_language, json_value
from .records import Observation, Record, notes_from_markdown, notes_to_markdown
from .site import Site
from .walk import MAX_IMAGES, sample

CHECKS = "_checks"
FILE = "expect.md"
RESULTS = ("agrees", "disagrees", "cannot tell")
HYPOTHESIS = re.compile(r"^- `hypothesis` (?!—)(.+)$")
EXPECT_LINE = re.compile(r"^holds: (?P<holds>.*?); fails: (?P<fails>.*?); visible: (?P<visible>yes|no)(?: \[[\d.]+\])?$")

EXPECT_SYSTEM = """You write, before seeing any photo, what photos of one field would show for each of a farm's hypotheses. The farm: <FIELD>.
The hypotheses are claims about the farm's ground, water, soil and history, by the farmer or an AI, not yet checked. They are not premises: write how a photo would test them.
How a hypothesis is checked here: mainly from the plants (which grow, how much, where, in what state), then the soil surface and the lie of the land as far as a photo of a field shows them.
For EVERY hypothesis, by its id:
- "holds": what photos of this field should show if it is true: concrete, visible signs (which plants and how dense, leaf colour and vigour, the soil surface: crust, cracks, puddles, colour, stones; slope; water).
- "fails": what would show it is false.
- "visible": false when no photo of the field can show it (events long past, rock or water at depth, places elsewhere, statistics); then "holds" and "fails" may say "not visible in a photo".
- "confidence": 0-1, how well a photo could tell.
Answer with a JSON array only, one object per hypothesis, in the order given:
[{"id": "h1", "holds", "fails", "visible": true | false, "confidence"}]"""

CHECK_SYSTEM = """You look at today's photos of a field of <FIELD> and answer, for each expectation written beforehand, which way the photos point.
Each expectation says what the photos should show if a hypothesis about the farm holds, and what if it fails.
For each id:
- "result": "agrees" when the photos show what "holds" says, "disagrees" when they show what "fails" says, "cannot tell" when the signs are not in view or point both ways.
- "seen": one sentence, in the words of what is in the photos (which plants, the soil, water), not a restatement of the expectation.
- "confidence": 0-1.
Prefer "cannot tell" to a stretch. Answer with a JSON array only: [{"id": "h3", "result", "seen", "confidence"}]"""


def hypotheses(records_root: Path) -> list[str]:
    """The `hypothesis` lines of site.md in file order (h1 is the first), marker
    taken off; the legend line and the how-to section are not claims."""
    p = records_root / "site.md"
    if not p.exists():
        return []
    body = _body(p).split(SITE_CHECK_HEADING)[0]
    return [m.group(1).strip() for line in body.splitlines() if (m := HYPOTHESIS.match(line))]


def path_for(records_root: Path, field: str) -> Path:
    return records_root / CHECKS / field / FILE


def load(records_root: Path, field: str) -> tuple[dict, list[Observation]] | None:
    p = path_for(records_root, field)
    return notes_from_markdown(p.read_text(encoding="utf-8")) if p.exists() else None


def build_expect_messages(field: str, hyps: list[str], records_root: Path) -> list[dict]:
    """Text only: the site's data and the numbered hypotheses; no photo, no reading of the field."""
    place = Site.load(records_root)
    numbered = "\n".join(f"h{i}: {h}" for i, h in enumerate(hyps, start=1))
    user = (f"{site_background(records_root)}\n\nThe field: {field}.\nHypotheses:\n{numbered}\n\n"
            "For each, what would photos of this field show? JSON only.")
    return [{"role": "system", "content": in_language(place.fill(EXPECT_SYSTEM))},
            {"role": "user", "content": place.fill(user)}]


def parse_expect(text: str, hyps: list[str]) -> list[Observation]:
    """One line per hypothesis, in order; one the model left out is said to be
    unanswered (and not visible), not invented."""
    got = {str(d.get("id", "")).strip().lower(): d for d in json_value(text) if isinstance(d, dict)}
    out = []
    for i in range(1, len(hyps) + 1):
        d = got.get(f"h{i}")
        if not d:
            out.append(Observation(f"h{i}", "holds: not answered; fails: not answered; visible: no"))
            continue
        holds, fails = (" ".join(str(d.get(k, "")).split()).replace(";", ",") for k in ("holds", "fails"))
        visible = "yes" if d.get("visible") is True or str(d.get("visible")).lower() in ("yes", "true") else "no"
        out.append(Observation(f"h{i}", f"holds: {holds}; fails: {fails}; visible: {visible}" + conf(d)))
    return out


def expect(field: str, root: Path, backend: Backend, today: str | None = None) -> Path:
    """Write records/_checks/<field>/expect.md from site.md's hypotheses (text only)."""
    records = root / "records"
    hyps = hypotheses(records)
    if not hyps:
        raise ValueError("no `hypothesis` lines in records/site.md")
    notes = parse_expect(chat(backend, build_expect_messages(field, hyps, records)), hyps)
    front = {"field": field, "date": today or date.today().isoformat(), "kind": "expect", "model": backend.name,
             "hypotheses": {f"h{i}": h for i, h in enumerate(hyps, start=1)}}
    p = path_for(records, field)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(notes_to_markdown(front, f"Expectations ({backend.name})", notes), encoding="utf-8")
    return p


def mark(records_root: Path, field: str, key: str, verdict: str | None, reason: str | None = None) -> Observation:
    """The farmer's right / wrong on one expectation (h3). A wrong one is not checked on photos."""
    if verdict not in ("right", "wrong", None):
        raise ValueError(f"verdict must be right or wrong, not {verdict!r}")
    got = load(records_root, field)
    if got is None:
        raise FileNotFoundError(f"no expectations for {field} yet; run fieldnotes expect {field}")
    front, notes = got
    line = next((o for o in notes if o.key == key), None)
    if line is None:
        raise KeyError(f"no expectation {key!r} for {field}")
    line.verdict = verdict
    line.reason = (" ".join(reason.split()) or None) if verdict and reason else None
    path_for(records_root, field).write_text(
        notes_to_markdown(front, f"Expectations ({front.get('model', 'none')})", notes), encoding="utf-8")
    return line


def to_check(records_root: Path, field: str) -> dict[str, dict]:
    """h → {"holds", "fails"}: the expectations photos can test, less those marked wrong."""
    got = load(records_root, field)
    out = {}
    for o in (got[1] if got else []):
        m = EXPECT_LINE.match(o.text)
        if m and m["visible"] == "yes" and o.verdict != "wrong":
            out[o.key] = {"holds": m["holds"], "fails": m["fails"]}
    return out


def build_check_messages(rec: Record, items: dict[str, dict], photo_root: Path, records_root: Path,
                         max_side: int = 1024) -> list[dict]:
    """The day's photos and the expectations; not the day's reading, so the
    check looks at the photos rather than at what was already said of them."""
    place = Site.load(records_root)
    listed = "\n".join(f"{h}: holds: {e['holds']}\n    fails: {e['fails']}" for h, e in items.items())
    content = [{"type": "text", "text": f"Expectations written beforehand:\n{listed}"},
               {"type": "text", "text": f"--- field {rec.field}, {day_summary(rec)}"},
               *_photo_parts(rec, photo_root, max_side, photos=sample(rec.photos, MAX_IMAGES)),
               {"type": "text", "text": "Which way do these photos point for each id? JSON only."}]
    return [{"role": "system", "content": in_language(place.fill(CHECK_SYSTEM))}, {"role": "user", "content": content}]


def parse_check(text: str, items: dict[str, dict]) -> list[Observation]:
    """Lines for the expectations asked about only, in h order; an id that was
    not asked (e.g. one photos cannot show) gets no line, whatever the model says."""
    out = []
    for d in json_value(text):
        if not isinstance(d, dict):
            continue
        h = str(d.get("id", "")).strip().lower()
        if h not in items or any(o.key == h for o in out):
            continue
        result = d.get("result") if d.get("result") in RESULTS else "cannot tell"
        out.append(Observation(h, f"{result}: {' '.join(str(d.get('seen', '')).split())}" + conf(d)))
    return sorted(out, key=lambda o: int(o.key[1:]))


def check_record(rec: Record, root: Path, backend: Backend) -> list[Observation]:
    """The Checks lines for one day's record; [] when the field has no expectations to test."""
    records = root / "records"
    items = to_check(records, rec.field)
    if not items or not rec.photos:
        return []
    return parse_check(chat(backend, build_check_messages(rec, items, root, records)), items)
