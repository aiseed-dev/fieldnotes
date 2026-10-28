"""Photos of the farm's neighbourhood: what the maps cannot show.

The farmer also photographs around the fields now and then: the neighbours'
fields and what they spray, the river bank, the abandoned plot next door that
sends seed, old houses and walls. Those photos are filed like a field's under
photos/_around/<date>/ (the 送る view has 「近所」) and read here, not by the
field pipeline: no SAM, no barometers, only what in them is likely to matter to
the fields. The reading is saved as records/_around/<date>.md, one line per
point, marked right or wrong like any other, and the newest one goes to every
later reading of the fields as background (describe.site_background).

Field photos and these show land, not houses or people, so they say little
about the farmer beyond where the farm is.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .inbox import AROUND
from .llm import Backend, chat, conf, in_language, json_value
from .records import Observation, Record
from .segment import load_image_as_data_url
from .site import Site

ASPECTS = ["land_use", "neighbours", "water", "seed_source", "animals", "history", "other"]

SYSTEM = """You look at photos taken around <FIELD>: not the field itself, but its neighbourhood (next-door fields and how they are worked, verges, the river or ditches, abandoned land, buildings, old walls, animals' signs).
Say what in them is likely to matter to the farmer's fields: neighbours' practices (herbicide-browned verges, bare tilled soil, fertiliser bags, burning), where weed seed and animals come from, water and drainage, and signs of how the land was used before.
Say only what the photos show or strongly suggest; mark guesses with a low confidence. Name which photo each point comes from (by its number).
Answer with JSON only: [{"aspect": one of %s, "text": one sentence, "confidence": 0-1}].""" % ASPECTS


def build_messages(photos: list[Path], max_side: int = 1024, place: Site | None = None) -> list[dict]:
    content: list[dict] = []
    for n, p in enumerate(photos, start=1):
        content.append({"type": "text", "text": f"--- photo {n}: {p.name}"})
        url, _, _ = load_image_as_data_url(p, max_side)
        content.append({"type": "image_url", "image_url": {"url": url}})
    content.append({"type": "text", "text": "What around the fields is likely to matter to them? JSON only."})
    return [{"role": "system", "content": in_language((place or Site()).fill(SYSTEM))}, {"role": "user", "content": content}]


def parse(text: str) -> list[Observation]:
    out = []
    for it in json_value(text):
        aspect = it.get("aspect", "other")
        out.append(Observation(key=aspect if aspect in ASPECTS else "other", text=it.get("text", "").strip() + conf(it)))
    return out


def read_around(root: Path, day: date | str, photos: list[str], backend: Backend) -> Record:
    """Read the neighbourhood photos of one day (paths relative to root)."""
    day_s = day if isinstance(day, str) else day.isoformat()
    records = root / "records"
    rec = Record(field=AROUND, date=day_s, photos=photos, ai_model=backend.name)
    rec.observations = parse(chat(backend, build_messages([root / p for p in photos], place=Site.load(records))))
    return rec


def latest_text(records_root: Path) -> str:
    """The newest neighbourhood reading, as background for the fields."""
    d = records_root / AROUND
    days = sorted(p.stem for p in d.glob("*.md")) if d.is_dir() else []
    if not days:
        return ""
    rec = Record.load(records_root, AROUND, days[-1])
    lines = "\n".join(o.to_line() for o in rec.observations)
    return f"The neighbourhood, from the farmer's photos of {days[-1]} (lines marked '→ farmer: wrong' are known wrong):\n{lines}"
