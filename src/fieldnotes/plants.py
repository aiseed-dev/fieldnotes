"""Why a weed dominates: ecology notes per species, kept as plain text.

When a weed becomes dominant in a field, its dominance says something about
the soil, water and history there. For each dominant species the model is
asked once why that plant dominates (pH, moisture, fertility, response to
mowing and disturbance, light, succession, roots); the answer is kept at

    records/_plants/<Genus_species>.md

Every line is a hypothesis with a confidence, written in the same line format
as the observation records, so the farmer can mark it right or wrong. The
notes are given to later observations as background to check against, not as
facts.

TODO: ask with search grounding so each note can carry a source, once the
Meta Model API parameter for it is confirmed. Until then the notes carry no
sources and say so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .llm import Backend, chat, conf, in_language, json_value
from .records import Observation, notes_from_markdown, notes_to_markdown
from .site import Site

PLANTS = "_plants"
ASPECTS = ["soil_ph", "moisture", "fertility", "mowing", "disturbance", "light", "succession", "roots", "other"]

ECOLOGY_SYSTEM = """You explain why a plant becomes dominant in a field, for a farmer who tends <FIELD>.
For the plant named, say what its dominance tells about the place: preferred soil pH, moisture, fertility, how it responds to mowing and to disturbance, light, which stage of succession it marks, and its roots.
Say only what is commonly reported for this plant as it grows in <REGION>. Where reports disagree or you are unsure, say so and give a low confidence. Do not invent sources.
Answer with JSON only: {"name": common name, "scientific": scientific name, "notes": [{"aspect": one of %s, "text": one sentence, "confidence": 0-1}]}.""" % ASPECTS

SPECIES = re.compile(r"(?P<name>[^;()]+?)\s*\((?P<sci>[A-Z][a-z]+ [a-z][a-z-]+)\)")


def slug(scientific: str) -> str:
    return scientific.strip().replace(" ", "_")


@dataclass
class PlantNote:
    name: str
    scientific: str
    model: str = ""
    written: str = ""
    notes: list[Observation] = field(default_factory=list)

    @staticmethod
    def path_for(root: Path, scientific: str) -> Path:
        return root / PLANTS / f"{slug(scientific)}.md"

    def to_markdown(self) -> str:
        front = {"name": self.name, "scientific": self.scientific, "status": "hypothesis",
                 "model": self.model, "written": self.written, "sources": "none yet (no search grounding)"}
        return notes_to_markdown(front, f"Why it dominates ({self.model or 'none'})", self.notes)

    @classmethod
    def from_markdown(cls, text: str) -> "PlantNote":
        front, notes = notes_from_markdown(text)
        return cls(name=front["name"], scientific=front["scientific"],
                   model=front.get("model", ""), written=str(front.get("written", "")), notes=notes)

    def save(self, root: Path) -> Path:
        p = self.path_for(root, self.scientific)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_markdown(), encoding="utf-8")
        return p


def species_in(observations: list[Observation]) -> list[tuple[str, str]]:
    """(Japanese name, scientific name) for each plant in the `dominant` observations."""
    out = []
    for o in observations:
        if o.key == "dominant":
            out += [(m["name"].strip(), m["sci"]) for m in SPECIES.finditer(o.text)]
    return out


def build_ecology_messages(name: str, scientific: str, place: Site | None = None) -> list[dict]:
    return [{"role": "system", "content": in_language((place or Site()).fill(ECOLOGY_SYSTEM))},
            {"role": "user", "content": f"{name} ({scientific}). JSON only."}]


def parse_ecology(text: str, name: str, scientific: str, model: str) -> PlantNote:
    d = json_value(text)
    note = PlantNote(name=d.get("name") or name, scientific=scientific, model=model, written=date.today().isoformat())
    for it in d.get("notes", []):
        aspect = it.get("aspect", "other")
        note.notes.append(Observation(key=aspect if aspect in ASPECTS else "other",
                                      text=it.get("text", "").strip() + conf(it)))
    return note


def ecology(name: str, scientific: str, root: Path, backend: Backend) -> PlantNote:
    """The ecology note for one species, from records/_plants/ or asked once and saved."""
    p = PlantNote.path_for(root, scientific)
    if p.exists():
        return PlantNote.from_markdown(p.read_text(encoding="utf-8"))
    note = parse_ecology(chat(backend, build_ecology_messages(name, scientific, Site.load(root))), name, scientific, backend.name)
    note.save(root)
    return note


def notes_for_prompt(root: Path, species: list[tuple[str, str]]) -> str:
    """Background text on the dominant plants already looked up. Lines the
    farmer marked wrong are passed on as wrong, with the reason."""
    blocks = []
    for name, sci in dict.fromkeys(species):
        p = PlantNote.path_for(root, sci)
        if not p.exists():
            continue
        note = PlantNote.from_markdown(p.read_text(encoding="utf-8"))
        lines = [f"{note.name} ({note.scientific}):"]
        for o in note.notes:
            if o.verdict == "wrong":
                lines.append(f"  - {o.key}: WRONG per the farmer: {o.text} ({o.reason or 'no reason given'})")
            else:
                lines.append(f"  - {o.key}: {o.text}" + ("  (farmer: right)" if o.verdict == "right" else ""))
        blocks.append("\n".join(lines))
    if not blocks:
        return ""
    return ("Why the dominant plants dominate, as looked up earlier. These are hypotheses with confidences, "
            "not facts; check them against what you see:\n" + "\n".join(blocks))
