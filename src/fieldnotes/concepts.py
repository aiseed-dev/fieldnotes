"""What SAM 3.1 is asked to find in each field, kept as a record the farmer corrects.

SAM 3.1 takes one short English noun phrase per request ("goldenrod",
"bare soil"). Which phrase finds ogi or a crimson-clover seedling in a given
field is not known in advance; it is found by trying, and wrong phrases are
expected. So the list lives with the field's records:

    records/_concepts/<field>.md

    - concept: goldenrod | for: セイタカアワダチソウ (Solidago altissima) | by: ai | last: 2026-10-28 23.4%, 12 objects
    - concept: pampas grass | for: オギ (Miscanthus sacchariflorus) | by: ai | last: 2026-10-28 no match  → farmer: wrong (try "reed")
    - concept: reed | for: オギ (Miscanthus sacchariflorus) | by: farmer | last: -

* The model proposes a phrase for each dominant plant that has none yet.
* Every SAM run writes what each phrase found ("last") so misses show.
* The farmer marks a phrase wrong (with a reason, optionally a replacement);
  wrong phrases are no longer asked, and are shown to the model so it does
  not propose them again.

What works is worth sharing: a phrase that finds ogi on one farm will likely
find it on another. So verdicts are also tallied, per plant, in a shared
library that holds no location or farm data and can travel with the code:

    shared/sam_concepts.md

    - concept: goldenrod | for: Solidago altissima | right: 3 | wrong: 0 | last reason: -
    - concept: pampas grass | for: Miscanthus sacchariflorus | right: 0 | wrong: 2 | last reason: finds susuki, not ogi

A field that needs a phrase takes the shared library's best one first (more
right than wrong) and asks the model only when there is none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .llm import Backend, chat, json_value
from .records import Observation, Record, notes_from_markdown, notes_to_markdown

CONCEPTS = "_concepts"
SHARED = Path("shared/sam_concepts.md")
BASE = [("bare soil", "裸地")]  # every field starts with these
SCI = re.compile(r"\(([A-Z][a-z]+ [a-z][a-z-]+)\)")

SYSTEM = """You choose the text prompts for SAM 3.1, a segmentation model, for photos of a natural-farming field in Tokushima, Japan.
SAM 3.1 takes ONE short English noun phrase per request and returns every matching object. It cannot take commas, lists, "or", negation, or positions ("left", "behind"). Zero matches is a normal answer.
For each plant given, propose the single noun phrase most likely to make SAM find that plant in a field photo: prefer a plain, common English name or a simple visual description over a scientific name. Do not reuse any phrase the farmer marked wrong.
Answer with JSON only: [{"scientific": as given, "noun": the phrase, "confidence": 0-1}]."""


@dataclass
class Concept:
    noun: str
    target: str
    by: str = "ai"
    last: str = "-"
    verdict: str | None = None
    reason: str | None = None

    @property
    def active(self) -> bool:
        return self.verdict != "wrong"

    def to_obs(self) -> Observation:
        text = f"{self.noun} | for: {self.target} | by: {self.by} | last: {self.last}"
        return Observation("concept", text, self.verdict, self.reason)

    @classmethod
    def from_obs(cls, o: Observation) -> "Concept":
        parts = [p.strip() for p in o.text.split("|")]
        kv = dict(p.split(": ", 1) for p in parts[1:] if ": " in p)
        return cls(noun=parts[0], target=kv.get("for", ""), by=kv.get("by", "ai"),
                   last=kv.get("last", "-"), verdict=o.verdict, reason=o.reason)


@dataclass
class FieldConcepts:
    field: str
    items: list[Concept] = field(default_factory=list)

    @staticmethod
    def path_for(root: Path, field: str) -> Path:
        return root / CONCEPTS / f"{field}.md"

    @classmethod
    def load(cls, root: Path, field: str) -> "FieldConcepts":
        p = cls.path_for(root, field)
        if not p.exists():
            return cls(field, [Concept(noun, target, by="default") for noun, target in BASE])
        front, notes = notes_from_markdown(p.read_text(encoding="utf-8"))
        return cls(front.get("field", field), [Concept.from_obs(o) for o in notes if o.key == "concept"])

    def save(self, root: Path) -> Path:
        p = self.path_for(root, self.field)
        p.parent.mkdir(parents=True, exist_ok=True)
        front = {"field": self.field, "status": "SAM prompts; the farmer marks wrong ones"}
        p.write_text(notes_to_markdown(front, "SAM 3.1 concepts", [c.to_obs() for c in self.items]), encoding="utf-8")
        return p

    def nouns(self) -> list[str]:
        return list(dict.fromkeys(c.noun for c in self.items if c.active))

    def covered(self, scientific: str) -> bool:
        return any(c.active and scientific in c.target for c in self.items)

    def mark(self, noun: str, verdict: str, reason: str | None = None, replacement: str | None = None) -> None:
        """The farmer's verdict on a phrase; a replacement is added as the farmer's own."""
        for c in self.items:
            if c.noun == noun and c.active:
                c.verdict, c.reason = verdict, reason
                if replacement:
                    self.items.append(Concept(replacement, c.target, by="farmer"))
                return
        raise KeyError(f"no active concept {noun!r} in {self.field}")

    def record(self, date: str, found: dict[str, tuple[float, int]]) -> None:
        """found: noun -> (mean cover %, objects) from one observation's photos."""
        for c in self.items:
            if c.active and c.noun in found:
                cover, n = found[c.noun]
                c.last = f"{date} {cover}%, {n} objects" if n else f"{date} no match"


def plant_key(target: str) -> str:
    """The shared library is keyed by scientific name, else by the target text."""
    m = SCI.search(target)
    return m.group(1) if m else target


@dataclass
class SharedEntry:
    noun: str
    plant: str
    right: int = 0
    wrong: int = 0
    last_reason: str = "-"

    def to_obs(self) -> Observation:
        return Observation("concept", f"{self.noun} | for: {self.plant} | right: {self.right} | "
                                      f"wrong: {self.wrong} | last reason: {self.last_reason}")

    @classmethod
    def from_obs(cls, o: Observation) -> "SharedEntry":
        parts = [x.strip() for x in o.text.split("|")]
        kv = dict(x.split(": ", 1) for x in parts[1:] if ": " in x)
        return cls(parts[0], kv.get("for", ""), int(kv.get("right", 0)), int(kv.get("wrong", 0)),
                   kv.get("last reason", "-"))


@dataclass
class SharedConcepts:
    path: Path
    entries: list[SharedEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path = SHARED) -> "SharedConcepts":
        if not path.exists():
            return cls(path)
        _, notes = notes_from_markdown(path.read_text(encoding="utf-8"))
        return cls(path, [SharedEntry.from_obs(o) for o in notes if o.key == "concept"])

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        front = {"about": "SAM 3.1 noun phrases per plant, with farmers' right/wrong tallies. No location or farm data."}
        self.path.write_text(notes_to_markdown(front, "Shared SAM 3.1 concepts", [e.to_obs() for e in self.entries]),
                             encoding="utf-8")
        return self.path

    def tally(self, noun: str, plant: str, verdict: str, reason: str | None = None) -> None:
        e = next((e for e in self.entries if e.noun == noun and e.plant == plant), None)
        if e is None:
            e = SharedEntry(noun, plant)
            self.entries.append(e)
        if verdict == "right":
            e.right += 1
        elif verdict == "wrong":
            e.wrong += 1
            e.last_reason = reason or "-"

    def best(self, plant: str) -> str | None:
        good = [e for e in self.entries if e.plant == plant and e.right > e.wrong]
        return max(good, key=lambda e: (e.right - e.wrong, e.right)).noun if good else None

    def known_wrong(self, plant: str) -> list[SharedEntry]:
        return [e for e in self.entries if e.plant == plant and e.wrong > e.right]


def build_messages(species: list[tuple[str, str]], wrong: list[Concept]) -> list[dict]:
    lines = [f"- {name} ({sci})" for name, sci in species]
    user = "Plants:\n" + "\n".join(lines)
    if wrong:
        user += "\n\nPhrases the farmer marked wrong; do not reuse:\n" + "\n".join(
            f'- "{c.noun}" for {c.target}: {c.reason or "no reason given"}' for c in wrong)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user + "\n\nJSON only."}]


def ensure(root: Path, field: str, species: list[tuple[str, str]], backend: Backend,
           shared: SharedConcepts | None = None) -> FieldConcepts:
    """Give every dominant plant without an active phrase one: the shared
    library's best if there is one, else one proposed by the model."""
    shared = shared or SharedConcepts.load()
    fc = FieldConcepts.load(root, field)
    missing = []
    for n, s in dict.fromkeys(species):
        if fc.covered(s):
            continue
        best = shared.best(s)
        if best:
            fc.items.append(Concept(best, f"{n} ({s})", by="shared"))
        else:
            missing.append((n, s))
    if missing:
        wrong = [c for c in fc.items if not c.active] + [
            Concept(e.noun, e.plant, verdict="wrong", reason=f"shared: {e.last_reason}")
            for _, s in missing for e in shared.known_wrong(s)]
        names = {s: n for n, s in missing}
        for it in json_value(chat(backend, build_messages(missing, wrong))):
            sci, noun = it.get("scientific", ""), (it.get("noun") or "").strip().lower()
            if sci in names and noun and noun not in {c.noun for c in wrong}:
                fc.items.append(Concept(noun, f"{names[sci]} ({sci})"))
    fc.save(root)
    return fc


def mark(root: Path, field: str, noun: str, verdict: str, reason: str | None = None,
         replacement: str | None = None, shared: SharedConcepts | None = None) -> None:
    """The farmer's verdict on a phrase: recorded in the field's list and
    tallied in the shared library."""
    shared = shared or SharedConcepts.load()
    fc = FieldConcepts.load(root, field)
    target = next(c.target for c in fc.items if c.noun == noun and c.active)
    fc.mark(noun, verdict, reason, replacement)
    fc.save(root)
    shared.tally(noun, plant_key(target), verdict, reason)
    shared.save()


def segment_field(rec: Record, photo_root: Path, records_root: Path, run=None):
    """Run SAM 3.1 with the field's active phrases on every photo of the
    observation, set rec.coverage to the mean cover per phrase, and write what
    each phrase found back into the field's concept list. `run` defaults to
    segment.segment_concepts (replaceable in tests)."""
    if run is None:
        from .segment import segment_concepts as run
    fc = FieldConcepts.load(records_root, rec.field)
    nouns = fc.nouns()
    results = [run(photo_root / p, nouns) for p in rec.photos]
    found = {}
    for noun in nouns:
        covers = [r.concepts[noun].coverage for r in results if noun in r.concepts]
        count = sum(len(r.concepts[noun].instances) for r in results if noun in r.concepts)
        found[noun] = (round(sum(covers) / len(covers), 1) if covers else 0.0, count)
    rec.coverage = {noun: cover for noun, (cover, _) in found.items()}
    fc.record(rec.date, found)
    fc.save(records_root)
    return results
