"""Plain-text observation records: one Markdown file per field per observation.

Layout (see docs/design.md §3):

    records/<field>/<date>.md

    ---
    field: north-ridge
    date: 2026-10-28
    photos: [...]
    weather: {...}
    coverage: {weed: 61.2, bare_soil: 18.5}
    ---

    ## AI observation (<model>)
    - key: text  → farmer: right | wrong (reason)

    ## Earlier AI lines
    - key: text  → farmer: wrong (reason)

    ## From the farmer's voice (<model>)
    - work: what the farmer did  → farmer: right | wrong (reason)
    - seen: what the farmer saw

    ## Checks (<model>)
    - h3: agrees | disagrees | cannot tell: what the photos showed  → farmer: ...

    ## Farmer note (<model>, <language>)
    free text (voice notes: one line each, "HH:MM transcript (file)")

"Checks" answers, from the day's photos, the expectations written beforehand
for the farm's hypotheses (check.py); it is absent when there are none.
"Earlier AI lines" holds lines the farmer marked that a re-run of the same day
replaced with different text (pipeline.merge_rerun); it is absent otherwise.

Both halves are written so that a person, a spreadsheet, or another model can
read them later without this code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import llm

FRONT = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.S)
OBS_LINE = re.compile(
    r"^- (?P<key>[a-z][a-z0-9_]*): (?P<text>.*?)(?:\s+→ farmer: (?P<verdict>right|wrong)(?: \((?P<reason>.*)\))?)?$"
)
EARLIER_HEADING = "## Earlier AI lines"
VOICE_HEADING = "## From the farmer's voice"
CHECKS_HEADING = "## Checks"


@dataclass
class Observation:
    key: str
    text: str
    verdict: str | None = None  # "right" | "wrong" | None (not yet verified)
    reason: str | None = None

    def to_line(self) -> str:
        s = f"- {self.key}: {self.text}"
        if self.verdict:
            s += f"  → farmer: {self.verdict}"
            if self.reason:
                s += f" ({self.reason})"
        return s


@dataclass
class Record:
    field: str
    date: str  # ISO yyyy-mm-dd
    photos: list[str] = field(default_factory=list)
    weather: dict = field(default_factory=dict)
    coverage: dict[str, float] = field(default_factory=dict)  # concept -> % of frame
    ai_model: str = ""
    observations: list[Observation] = field(default_factory=list)
    earlier: list[Observation] = field(default_factory=list)  # marked lines a re-run replaced
    voice: list[Observation] = field(default_factory=list)  # work and seen, sorted from the farmer's voice
    voice_model: str = ""
    checks: list[Observation] = field(default_factory=list)  # the hypotheses checked on the day's photos
    checks_model: str = ""
    note_model: str = ""
    note_language: str = ""  # the language the note is in; the setting when new
    farmer_note: str = ""

    # ---- paths --------------------------------------------------------
    @staticmethod
    def path_for(root: Path, field: str, date: str) -> Path:
        return root / field / f"{date}.md"

    # ---- serialisation ------------------------------------------------
    def to_markdown(self) -> str:
        front = {
            "field": self.field,
            "date": self.date,
            "photos": self.photos,
            "weather": self.weather,
            "coverage": self.coverage,
        }
        out = ["---", yaml.safe_dump(front, sort_keys=False, allow_unicode=True).rstrip(), "---", ""]
        out.append(f"## AI observation ({self.ai_model or 'none'})")
        out += [o.to_line() for o in self.observations] or ["(none)"]
        out.append("")
        if self.earlier:
            out.append(EARLIER_HEADING)
            out += [o.to_line() for o in self.earlier]
            out.append("")
        if self.voice:
            out.append(f"{VOICE_HEADING} ({self.voice_model or 'none'})")
            out += [o.to_line() for o in self.voice]
            out.append("")
        if self.checks:
            out.append(f"{CHECKS_HEADING} ({self.checks_model or 'none'})")
            out += [o.to_line() for o in self.checks]
            out.append("")
        out.append(f"## Farmer note ({self.note_model or 'none'}, {self.note_language or llm.language()})")
        out.append(self.farmer_note or "(none)")
        out.append("")
        return "\n".join(out)

    @classmethod
    def from_markdown(cls, text: str) -> "Record":
        m = FRONT.match(text)
        if not m:
            raise ValueError("no YAML front matter")
        front = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        rec = cls(
            field=front["field"],
            date=str(front["date"]),
            photos=list(front.get("photos") or []),
            weather=dict(front.get("weather") or {}),
            coverage=dict(front.get("coverage") or {}),
        )
        section = None
        note_lines: list[str] = []
        for line in body.splitlines():
            if line.startswith(EARLIER_HEADING):
                section = "earlier"
                continue
            if line.startswith(VOICE_HEADING):
                section = "voice"
                rec.voice_model = line[len(VOICE_HEADING) :].strip(" ()")
                continue
            if line.startswith(CHECKS_HEADING):
                section = "checks"
                rec.checks_model = line[len(CHECKS_HEADING) :].strip(" ()")
                continue
            if line.startswith("## AI observation"):
                section = "ai"
                rec.ai_model = line[len("## AI observation") :].strip(" ()")
                continue
            if line.startswith("## Farmer note"):
                section = "note"
                head = [x.strip() for x in line[len("## Farmer note") :].strip(" ()").split(",")]
                rec.note_model = head[0]
                rec.note_language = head[1] if len(head) > 1 else ""
                continue
            if section in ("ai", "earlier", "voice", "checks"):
                om = OBS_LINE.match(line)
                if om:
                    {"ai": rec.observations, "earlier": rec.earlier, "voice": rec.voice,
                     "checks": rec.checks}[section].append(
                        Observation(**om.groupdict()))
            elif section == "note":
                note_lines.append(line)
        rec.farmer_note = "\n".join(note_lines).strip()
        if rec.farmer_note == "(none)":
            rec.farmer_note = ""
        return rec

    def save(self, root: Path) -> Path:
        p = self.path_for(root, self.field, self.date)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_markdown(), encoding="utf-8")
        return p

    @classmethod
    def load(cls, root: Path, field: str, date: str) -> "Record":
        return cls.from_markdown(cls.path_for(root, field, date).read_text(encoding="utf-8"))


def previous_records(root: Path, field: str, before: str, n: int) -> list[Record]:
    """The n most recent records for `field` dated strictly before `before`."""
    d = root / field
    if not d.exists():
        return []
    dates = sorted(p.stem for p in d.glob("*.md") if p.stem < before)
    return [Record.load(root, field, x) for x in dates[-n:]]


def corrected_examples(records: list[Record]) -> list[tuple[str, str, str]]:
    """(key, ai_text, reason) for every observation the farmer marked wrong.

    Fed back into the next observation's describe prompt as few-shot corrections.
    """
    out = []
    for r in records:
        for o in r.observations:
            if o.verdict == "wrong":
                out.append((o.key, o.text, o.reason or ""))
    return out


# ---- note files ---------------------------------------------------------
# Plant ecology notes, the surroundings reading and proposals share one shape:
# YAML front matter, one heading, then observation lines the farmer can mark.

def notes_to_markdown(front: dict, heading: str, notes: list[Observation]) -> str:
    out = ["---", yaml.safe_dump(front, sort_keys=False, allow_unicode=True).rstrip(), "---", ""]
    out.append(f"## {heading}")
    out += [o.to_line() for o in notes] or ["(none)"]
    out.append("")
    return "\n".join(out)


def notes_from_markdown(text: str) -> tuple[dict, list[Observation]]:
    m = FRONT.match(text)
    if not m:
        raise ValueError("no YAML front matter")
    notes = [Observation(**om.groupdict()) for line in m.group(2).splitlines() if (om := OBS_LINE.match(line))]
    return yaml.safe_load(m.group(1)) or {}, notes
