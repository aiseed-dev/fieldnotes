"""One field over time, in Markdown: what was seen, done, read and checked, day by day.

    ## 2026-10-28
    photos: photos/uncut/2026-10-28/121701-uncut.jpg
    weather: tmax 18.4, tmin 12.3, rain_mm 0.0
    overall: Dense head-high stand ...  → farmer: right
    zone: S edge: the cut strip, stubble and bare soil (photos 30, 31) [0.7]
    emerging: ヘアリーベッチ (Vicia villosa) at S edge (photos 31) [0.5]  → farmer: right
    work: 北側の通路だけ刈った
    seen: オギの株元に新しい芽
    farmer: 3 ✓, 1 ✗ of 6 AI lines
    cut proposal: summary: South edge first ...  → farmer: wrong (...)
    checks: h3 agrees ✓, h7 cannot tell, h12 disagrees ✗

Oldest first, so it reads as a story. Two tables follow: what was sown or
planted coming up (`emerging`, one row per species, one column per day: where,
and the farmer's mark), so the course of a mixed sowing reads across; and,
when the field's photos were checked against the hypotheses (check.py), each
hypothesis with the day's answer and the farmer's mark. Used by `fieldnotes timeline` and the
MCP `timeline` tool, and for the demo.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import check
from .propose import HEADINGS, PROPOSALS, Proposal
from .records import Record

MARKS = {"right": " ✓", "wrong": " ✗", None: ""}
CONF = re.compile(r"\s*\[[\d.]+\]$")

WEATHER_KEYS = ("tmax", "tmin", "rain_mm", "days_since_rain")


def _proposals(records_root: Path, field: str, day: str) -> list[Proposal]:
    d = records_root / PROPOSALS / field
    return [Proposal.from_markdown(p.read_text(encoding="utf-8")) for p in sorted(d.glob(f"{day}-*.md"))] if d.exists() else []


def _days(records_root: Path, field: str) -> list[str]:
    days = {p.stem for p in (records_root / field).glob("*.md")}
    d = records_root / PROPOSALS / field
    if d.exists():
        days |= {p.name[:10] for p in d.glob("*.md")}
    return sorted(days)


def _answer(o) -> str:
    return o.text.split(":", 1)[0] + MARKS.get(o.verdict, "")


def _records(records_root: Path, field: str, days: list[str]) -> dict[str, Record]:
    return {d: Record.load(records_root, field, d) for d in days if Record.path_for(records_root, field, d).exists()}


def emerging_table(records_root: Path, field: str, days: list[str]) -> list[str]:
    """One row per species seen coming up, one column per day it was read."""
    cols = {}
    for day, rec in _records(records_root, field, days).items():
        lines = [o for o in rec.observations if o.key == "emerging"]
        if lines:
            cols[day] = {}
            for o in lines:
                name, _, where = o.text.partition(" at ")
                where = CONF.sub("", where)
                cols[day][name] = (cols[day][name] + "; " if name in cols[day] else "") + where + MARKS.get(o.verdict, "")
    if not cols:
        return []
    names = list(dict.fromkeys(n for c in cols.values() for n in c))
    out = ["## Coming up day by day", "", "| species | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    out += [f"| {n} | " + " | ".join(c.get(n, "") for c in cols.values()) + " |" for n in names]
    return out + [""]


def checks_table(records_root: Path, field: str, days: list[str]) -> list[str]:
    """One row per hypothesis checked on this field's photos, one column per day."""
    cols = {}
    for day in days:
        if Record.path_for(records_root, field, day).exists():
            rec = Record.load(records_root, field, day)
            if rec.checks:
                cols[day] = {o.key: o for o in rec.checks}
    if not cols:
        return []
    hs = sorted({h for c in cols.values() for h in c}, key=lambda h: int(h[1:]))
    got = check.load(records_root, field)
    names = (got[0].get("hypotheses") or {}) if got else {}
    short = lambda h: (lambda s: s if len(s) <= 48 else s[:47] + "…")(names.get(h, ""))  # noqa: E731
    out = ["## Hypotheses day by day", "", "| hypothesis | " + " | ".join(cols) + " |",
           "|---|" + "---|" * len(cols)]
    for h in hs:
        out.append(f"| {h} {short(h)} | " + " | ".join(_answer(c[h]) if h in c else "" for c in cols.values()) + " |")
    return out + [""]


def timeline(field: str, records_root: Path, since: str | None = None) -> str:
    out = [f"# {field}: timeline", ""]
    days = [d for d in _days(records_root, field) if not since or d >= since]
    for day in days:
        out.append(f"## {day}")
        if Record.path_for(records_root, field, day).exists():
            rec = Record.load(records_root, field, day)
            if rec.photos:
                out.append("photos: " + ", ".join(rec.photos))
            wx = ", ".join(f"{k} {rec.weather[k]}" for k in WEATHER_KEYS if k in rec.weather)
            if wx:
                out.append(f"weather: {wx}")
            out += [o.to_line()[2:] for o in rec.observations if o.key in ("overall", "zone", "emerging")]
            out += [o.to_line()[2:] for o in rec.voice]
            if rec.observations:
                right = sum(o.verdict == "right" for o in rec.observations)
                wrong = sum(o.verdict == "wrong" for o in rec.observations)
                out.append(f"farmer: {right} ✓, {wrong} ✗ of {len(rec.observations)} AI lines ({rec.ai_model})")
            if rec.checks:
                out.append("checks: " + ", ".join(f"{o.key} {_answer(o)}" for o in rec.checks))
        for prop in _proposals(records_root, field, day):
            head = HEADINGS.get(prop.kind, prop.kind).replace(" proposal", "").lower()
            out += [f"{head} proposal: {o.to_line()[2:]}" for o in prop.notes if o.key == "summary"]
        out.append("")
    out += emerging_table(records_root, field, days)
    out += checks_table(records_root, field, days)
    if not days:
        out.append("(no records yet)")
    return "\n".join(out).rstrip() + "\n"
