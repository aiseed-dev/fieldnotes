"""Where the farm is and how it is farmed, from the front matter of records/site.md.

Every prompt starts from "a field in <place>", the weather
needs the coordinates, and the surroundings need to know which map service
covers the spot. None of that is written into the code, so the same code
serves any farm: `fieldnotes init` writes a site.md for a new one.

    ---
    place: Tokushima, Japan
    country: JP
    lat: 34.0801
    lon: 134.4454
    climate: warm temperate, humid
    method: no tillage, no fertiliser, no pesticide, Fukuoka method; weeds are cut, not pulled
    ---

Prompts carry the tokens <FIELD> ("a field in Tokushima, Japan (warm
temperate, humid; no tillage, ...)") and <REGION> ("Tokushima, Japan"); `fill`
puts this farm's values in. The `method` line is the farm's own words; the app
has no method of its own (2026-11-03, the farmer: the app is for many farms, not
one method's). A farm whose site.md has no `method` line, or none at all, runs
with "how the farm is worked: not recorded yet" in its prompts and no weather.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FILE = "site.md"
METHOD = ""  # the app's default: none; a farm's own words go in its site.md (`fieldnotes init --method`)
UNRECORDED = "not recorded yet"  # what site.md says, and the prompt, until the farmer writes the line
FRONT = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


@dataclass
class Site:
    place: str = ""
    country: str = ""  # ISO 3166 alpha-2, e.g. "JP"; picks the map service
    lat: float | None = None
    lon: float | None = None
    climate: str = ""
    method: str = METHOD

    @classmethod
    def load(cls, records_root: Path) -> "Site":
        p = records_root / FILE
        m = FRONT.match(p.read_text(encoding="utf-8")) if p.exists() else None
        front = (yaml.safe_load(m.group(1)) or {}) if m else {}
        return cls(place=str(front.get("place") or ""), country=str(front.get("country") or "").upper(),
                   lat=front.get("lat"), lon=front.get("lon"), climate=str(front.get("climate") or ""),
                   method=_method(front.get("method")))

    @property
    def located(self) -> bool:
        return self.lat is not None and self.lon is not None

    def region(self) -> str:
        return self.place or "the farmer's region"

    def field(self) -> str:
        where = f" in {self.place}" if self.place else ""
        how = self.method or f"how the farm is worked: {UNRECORDED}"
        about = "; ".join(x for x in (self.climate, how) if x)
        return f"a field{where} ({about})"

    def fill(self, prompt: str) -> str:
        return prompt.replace("<FIELD>", self.field()).replace("<REGION>", self.region())


def _method(text) -> str:
    """The farm's own `method` line; empty when there is none or it only says "not recorded yet"."""
    text = str(text or "").strip()
    return "" if text.lower() == UNRECORDED else text


def template(place: str, country: str, lat: float, lon: float, climate: str = "", method: str = METHOD) -> str:
    """A new farm's site.md: the front matter plus empty sections to fill in. Without `method`
    the line says "not recorded yet" so the farmer sees what to write."""
    front = {"place": place, "country": country.upper(), "lat": lat, "lon": lon, "climate": climate,
             "method": _method(method) or UNRECORDED}
    return "---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + """---

# Site profile

What is known or believed about the farm. Every line is a claim with a source
and a status, so a reader (or a model) can tell data from belief:

- `data` — a public measurement or record, with its source.
- `record` — something the farmer did or saw (dates, actions). Not a theory.
- `hypothesis` — a reading of the field, by the farmer or by the AI, not yet checked.
- `supported` / `refuted` — checked; the evidence is named on the line.

Hypotheses are **not** given to the model as premises. They are things to check.

## Terrain and water

## Geology and soil

## History of the land

## What the farmer knows works here (and what does not)
"""
