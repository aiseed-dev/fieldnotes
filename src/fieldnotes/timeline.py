"""One field over time, in Markdown: what was seen, done, read and checked, day by day.

    ## 2026-10-28
    photos: photos/uncut/2026-10-28/121701-uncut.jpg
    weather: tmax 18.4, tmin 12.3, rain_mm 0.0
    overall: Dense head-high stand ...  → farmer: right
    work: 北側の通路だけ刈った
    seen: オギの株元に新しい芽
    farmer: 3 ✓, 1 ✗ of 6 AI lines
    cut proposal: summary: South edge first ...  → farmer: wrong (...)

Oldest first, so it reads as a story. Used by `fieldnotes timeline` and the
MCP `timeline` tool, and for the demo.
"""

from __future__ import annotations

from pathlib import Path

from .propose import HEADINGS, PROPOSALS, Proposal
from .records import Record

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
            out += [o.to_line()[2:] for o in rec.observations if o.key == "overall"]
            out += [o.to_line()[2:] for o in rec.voice]
            if rec.observations:
                right = sum(o.verdict == "right" for o in rec.observations)
                wrong = sum(o.verdict == "wrong" for o in rec.observations)
                out.append(f"farmer: {right} ✓, {wrong} ✗ of {len(rec.observations)} AI lines ({rec.ai_model})")
        for prop in _proposals(records_root, field, day):
            head = HEADINGS.get(prop.kind, prop.kind).replace(" proposal", "").lower()
            out += [f"{head} proposal: {o.to_line()[2:]}" for o in prop.notes if o.key == "summary"]
        out.append("")
    if not days:
        out.append("(no records yet)")
    return "\n".join(out).rstrip() + "\n"
