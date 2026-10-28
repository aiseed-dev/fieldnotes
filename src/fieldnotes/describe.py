"""Describe today's photos against the previous observations with Muse Spark (or Glimmer).

The model gets, in ONE request:
  * the photos of the same field from the last N observations and today, oldest first,
  * the SAM 3.1 coverage numbers for each observation (a rough guide),
  * the weather for each observation day,
  * the site background from records/site.md (terrain, geology, soil, from
    public maps where available, each line marked data / hypothesis / refuted)
    and the surroundings read from GSI maps (records/surroundings.md),
  * why the dominant plants dominate, as looked up earlier (plants.py),
  * the farmer's earlier corrections (few-shot),
and answers, in this order: the field as a whole, the dominant weeds, how the
vegetables grow, the weed barometers (acidity, fertility, dryness), then what
CHANGED. Natural farming looks at the whole field before details, so the
overall view always comes first and the numbers only support it.

The barometers are a holistic judgment: start from why the dominant weeds
dominate, then check against the vegetables, the weather and the site's
geology and soil.

`compare_fields` puts the latest observation of several fields side by side and
ranks them on the same barometers. `observe` runs one observation end to end.
"""

from __future__ import annotations

import json
from pathlib import Path

from .llm import Backend, chat, conf, in_language, json_value
from .plants import ecology, notes_for_prompt, species_in
from .records import FRONT, Observation, Record, corrected_examples
from .segment import load_image_as_data_url

# Weed barometers: what "up" and "down" mean, how the rough level is given,
# and how fields are ranked (from which end).
BAROMETERS = {
    "acidity": {"up": "more acidic", "down": "less acidic",
                "level": 'an approximate pH range, e.g. "5.5-6.5"', "rank": "most acidic → least acidic"},
    "fertility": {"up": "richer", "down": "poorer",
                  "level": 'one of "poor", "moderate", "rich"', "rank": "richest → poorest"},
    "dryness": {"up": "drier", "down": "wetter",
                "level": 'one of "dry", "moist", "wet"', "rank": "driest → wettest"},
}
CHANGE_KEYS = ["leaf_colour", "weed_height", "soil", "animal", "other"]
KEYS = ["overall", "dominant", "crops", *BAROMETERS, *CHANGE_KEYS]

FIELD_CONTEXT = """You observe a natural-farming field in Tokushima, Japan (no tillage, no fertiliser, no pesticide, Fukuoka method).
Weeds are ground cover here, not enemies: report them as a condition, not a problem.
The farmer chooses how many photos and from where; file names may say which part of the field a photo shows.
Cover percentages from a segmentation model are a rough guide to how the whole moves, not a precise measurement."""

BAROMETER_RULES = """Weed barometers: the soil's acidity, fertility and dryness, as one holistic judgment.
- Start from WHY the dominant weeds dominate: what their dominance says about pH, moisture and fertility (background on them is given below where known).
- Read from the whole combination of plants and their proportions, not from a single indicator species, and read their state too: leaf colour (yellowing, purple tints), vigour, height, density, flowering, wilting.
- Check that reading against how the vegetables are growing, against the weather (days since rain) for dryness, and against the site's terrain, geology, soil and surroundings (neighbouring land use, water, seed sources). In the site background, lines marked `data` come from public maps and records; `hypothesis` lines are unchecked readings and `refuted` lines are known to be wrong. When the signs point different ways, say so and lower the confidence.
- Give a rough level: acidity as %s; fertility as %s; dryness as %s. Never more precise than that.
- Fertility means what the plants can actually take up, as their growth shows, not how much mineral the soil holds. This soil is mineral-rich schist silt; the question is whether roots and soil life make it available. Rock minerals carry almost no nitrogen and this soil is low in organic matter, so watch nitrogen signs (pale or yellowing older leaves, how legumes do) apart from other minerals.
- In "evidence", name which plants (weeds and vegetables) and what about them led you there.
- If the plants do not tell, use "unclear" and a low confidence rather than guessing.""" % (
    BAROMETERS["acidity"]["level"], BAROMETERS["fertility"]["level"], BAROMETERS["dryness"]["level"])

SYSTEM = FIELD_CONTEXT + """
You will receive photos of the SAME field from earlier observations and today, oldest first, each observation with its cover percentages and weather.

""" + BAROMETER_RULES + """

Answer with a JSON array only, in this order:
1. {"key": "overall", "text": one or two sentences on how the field looks as a whole today (vigour, colour, the mix of plants, unevenness across the field) and how that whole has shifted since the earlier observations, "confidence": 0-1}. Always present.
2. {"key": "dominant", "plants": [{"name": Japanese name, "scientific": scientific name, "share": rough share of the field such as "~40%%"}], "confidence"}: the 2 to 4 weeds that dominate today, most dominant first. Always present.
3. {"key": "crops", "text": how the vegetables are growing as a whole (vigour, leaf colour, size, evenness, signs of stress), "confidence"}. Omit if no vegetables are in view.
4. For each of "acidity", "fertility", "dryness": {"key", "level", "direction": "up" | "down" | "same" | "unclear" compared with the most recent earlier observation (up = more acidic / richer / drier), "evidence", "confidence"}. If there is no earlier observation, use "direction": "none".
5. Then only what CHANGED since the earlier observations: {"key": one of %s, "text": one short sentence, "confidence"}. Omit a key if nothing changed. Say "no new tracks" for animal only if you looked and saw none.
Do not advise, do not predict, do not count or describe single plants.""" % json.dumps(CHANGE_KEYS)

COMPARE_SYSTEM = FIELD_CONTEXT + """
You will receive the latest photos of SEVERAL fields of the same farm, each introduced by its field name, with its cover percentages, weather and the weeds that dominated there.

""" + BAROMETER_RULES + """

Answer with a JSON array only, in this order:
1. {"key": "overall", "text": one or two sentences on how the fields differ as wholes, "confidence": 0-1}.
2. For each of "acidity", "fertility", "dryness": {"key", "order": field names ranked from the most acidic / richest / driest end, leaving out any field you cannot place, "levels": {field name: level}, "evidence", "confidence"}.
Do not advise, do not predict, do not count or describe single plants."""


def day_summary(rec: Record) -> str:
    cov = ", ".join(f"{k} {v}%" for k, v in rec.coverage.items()) or "n/a"
    wx = ", ".join(f"{k} {v}" for k, v in rec.weather.items()) or "n/a"
    return f"{rec.date}: cover [{cov}]; weather [{wx}]"


def _photo_parts(rec: Record, photo_root: Path, max_side: int) -> list[dict]:
    parts: list[dict] = []
    for p in rec.photos:
        parts.append({"type": "text", "text": f"photo {Path(p).name}"})
        url, _, _ = load_image_as_data_url(photo_root / p, max_side)
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def _corrections_part(records: list[Record]) -> list[dict]:
    corrections = corrected_examples(records)
    if not corrections:
        return []
    lines = ["The farmer corrected these earlier observations; do not repeat the mistake:"]
    for key, text, reason in corrections:
        lines.append(f'- {key}: "{text}" was wrong: {reason}')
    return [{"type": "text", "text": "\n".join(lines)}]


def _text_part(text: str) -> list[dict]:
    return [{"type": "text", "text": text}] if text else []


SITE_CHECK_HEADING = "## How a hypothesis is checked"


def _body(p: Path) -> str:
    text = p.read_text(encoding="utf-8")
    m = FRONT.match(text)
    return (m.group(2) if m else text).strip()


def site_background(records_root: Path) -> str:
    """records/site.md (without its how-to section), plus the surroundings read
    from the GSI maps (records/surroundings.md) if that has been done."""
    parts = []
    site = records_root / "site.md"
    if site.exists():
        parts.append("Site background (records/site.md):\n" + _body(site).split(SITE_CHECK_HEADING)[0].strip())
    around = records_root / "surroundings.md"
    if around.exists():
        parts.append("Surroundings, read from GSI maps (hypotheses; lines marked '→ farmer: wrong' are known wrong):\n"
                     + _body(around))
    return "\n\n".join(parts)


def build_messages(today: Record, previous: list[Record], photo_root: Path,
                   plant_notes: str = "", max_side: int = 1280, site: str = "") -> list[dict]:
    """Pure function: records -> chat messages (with images inline). Testable offline."""
    content: list[dict] = []
    for rec in previous + [today]:
        label = "TODAY" if rec is today else "earlier"
        content.append({"type": "text", "text": f"--- {label} {day_summary(rec)}"})
        content += _photo_parts(rec, photo_root, max_side)
    content += _text_part(site)
    content += _text_part(plant_notes)
    content += _corrections_part(previous)
    content.append({"type": "text", "text": "How does the field look as a whole today, which weeds dominate, how are the vegetables growing, what does all that say about acidity, fertility and dryness, and what changed? JSON array only, overall first."})
    return [{"role": "system", "content": in_language(SYSTEM)}, {"role": "user", "content": content}]


def build_compare_messages(latest: list[Record], photo_root: Path, history: list[Record] = (),
                           plant_notes: str = "", max_side: int = 1024, site: str = "") -> list[dict]:
    """latest: one record per field (its newest observation). history: earlier
    comparison records, whose farmer corrections are fed back."""
    content: list[dict] = []
    for rec in latest:
        dom = "; ".join(o.text for o in rec.observations if o.key == "dominant") or "n/a"
        content.append({"type": "text", "text": f"--- FIELD {rec.field} {day_summary(rec)}; dominant [{dom}]"})
        content += _photo_parts(rec, photo_root, max_side)
    content += _text_part(site)
    content += _text_part(plant_notes)
    content += _corrections_part(list(history))
    content.append({"type": "text", "text": "How do these fields differ, and how do they rank on acidity, fertility and dryness? JSON array only, overall first."})
    return [{"role": "system", "content": in_language(COMPARE_SYSTEM)}, {"role": "user", "content": content}]


def _level(key: str, level) -> str:
    level = str(level or "unclear").strip()
    return f"pH ~{level}" if key == "acidity" and level[:1].isdigit() else level


def _order_key(o: Observation) -> int:
    order = ["overall", "dominant", "crops", *BAROMETERS]
    return order.index(o.key) if o.key in order else len(order)


def parse_observations(text: str, basis: str | None = None) -> list[Observation]:
    """Model answer -> observations. `basis` is the date of the earlier
    observation the barometer directions refer to."""
    out = []
    for it in json_value(text):
        key = it.get("key", "other")
        if key == "dominant":
            plants = "; ".join(f"{p.get('name', '?')} ({p.get('scientific', '?')}) {p.get('share', '')}".strip()
                               for p in it.get("plants", []))
            out.append(Observation(key=key, text=(plants or "unclear") + conf(it)))
            continue
        if key in BAROMETERS:
            b = BAROMETERS[key]
            parts = [_level(key, it.get("level"))]
            d = it.get("direction")
            if d in ("up", "down"):
                parts.append(f"{b[d]} than {basis or 'before'}")
            elif d in ("same", "unclear"):
                parts.append(f"{d} vs {basis or 'before'}")
            parts.append(f"evidence: {it.get('evidence', '').strip()}")
            out.append(Observation(key=key, text="; ".join(parts) + conf(it)))
            continue
        if key not in KEYS:
            key = "other"
        out.append(Observation(key=key, text=it.get("text", "").strip() + conf(it)))
    out.sort(key=_order_key)  # stable: overall, dominant, crops, acidity, fertility, dryness, then changes
    return out


def parse_comparison(text: str, fields: list[str]) -> list[Observation]:
    out = []
    for it in json_value(text):
        key = it.get("key", "other")
        if key in BAROMETERS:
            levels = it.get("levels") or {}
            order = [f for f in it.get("order", []) if f in fields]
            ranked = " > ".join(f"{f} ({_level(key, levels.get(f))})" for f in order) or "unclear"
            txt = f"{BAROMETERS[key]['rank']}: {ranked}; evidence: {it.get('evidence', '').strip()}"
            out.append(Observation(key=key, text=txt + conf(it)))
        elif key == "overall":
            out.append(Observation(key=key, text=it.get("text", "").strip() + conf(it)))
    out.sort(key=_order_key)
    return out


def describe(today: Record, previous: list[Record], photo_root: Path, backend: Backend,
             plant_notes: str = "", site: str = "") -> list[Observation]:
    text = chat(backend, build_messages(today, previous, photo_root, plant_notes, site=site))
    return parse_observations(text, basis=previous[-1].date if previous else None)


def observe(today: Record, previous: list[Record], photo_root: Path, records_root: Path,
            backend: Backend) -> Record:
    """One observation: background on the plants that dominated before, the
    model's reading, then a look-up of any newly dominant plant for next time."""
    known = [s for r in previous for s in species_in(r.observations)]
    today.observations = describe(today, previous, photo_root, backend,
                                  notes_for_prompt(records_root, known), site_background(records_root))
    today.ai_model = backend.name
    for name, sci in species_in(today.observations):
        ecology(name, sci, records_root, backend)  # cached under records/_plants/
    return today


COMPARE = "_compare"  # records/_compare/<date>.md holds the field-to-field comparisons


def compare_fields(latest: list[Record], photo_root: Path, records_root: Path, backend: Backend,
                   history: list[Record] = ()) -> Record:
    """Rank fields on the weed barometers. Returns a record to save under
    records/_compare/, so the farmer can mark it right or wrong like any other."""
    species = [s for r in latest for s in species_in(r.observations)]
    messages = build_compare_messages(latest, photo_root, history, notes_for_prompt(records_root, species),
                                      site=site_background(records_root))
    return Record(
        field=COMPARE,
        date=max(r.date for r in latest),
        photos=[p for r in latest for p in r.photos],
        ai_model=backend.name,
        observations=parse_comparison(chat(backend, messages), [r.field for r in latest]),
    )
