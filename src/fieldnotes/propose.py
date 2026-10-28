"""Propose a cover-crop (green manure) mix for one field, from its own records.

Reading the field (describe.py) comes first; this is the first step that puts
something forward. The model gets everything the records hold about the field:

  * the latest observation: overall view, dominant weeds, how the vegetables
    grow, and the acidity / fertility / dryness barometers,
  * why the dominant weeds dominate (records/_plants/),
  * the site background and surroundings (site.md, surroundings.md), where the
    farmer's own knowledge lives (e.g. "hairy vetch is too strong here"),
  * the date, so it proposes what can be sown now where the farm is,
  * the seeds the farmer has on hand, if given,
  * earlier proposals for this field and the farmer's right/wrong on them,

and answers with a mix: each species with its role, a rough share and the
reason for this field; when and how to sow; cautions; and how to tell from
later photos whether it worked. The proposal is saved at

    records/_proposals/<field>/<date>-cover_crop.md

one line per point, so the farmer marks each right or wrong like any other
record, and later observations answer the "watch" lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .describe import site_background
from .llm import Backend, chat, conf, in_language, json_value
from .plants import notes_for_prompt, species_in
from .records import Observation, Record, corrected_examples, notes_from_markdown, notes_to_markdown
from .site import Site

PROPOSALS = "_proposals"
KIND = "cover_crop"
ROLES = ["root_tillage", "nitrogen", "taproot", "mycorrhiza", "ground_cover", "biomass", "flowers", "other"]

SYSTEM = """You propose a cover-crop (green manure) mix for <FIELD>.
Everything you know about this field is below: its latest observation, why its dominant weeds dominate, its terrain, geology, soil and surroundings, and the farmer's own knowledge. Base the proposal on THIS field, and say for each choice what in these records it answers.
Rules:
- Propose a MIX, not a single species: species that share the work by role (%s). Diversity is the aim, as in regenerative agriculture.
- Only species that can be sown now, at this date, in <REGION>. If seeds on hand are listed, build the mix from them first and say what, if anything, is worth adding.
- Respect the farmer's knowledge in the site background: never propose what the farmer says does not work here, and say so if you leave something common out for that reason.
- Remember that brassicas do not host mycorrhizal fungi, that legumes need their rhizobia (say if inoculant is advisable), and that a strong grass can shade out legumes.
- Give rough shares of the mix, not precise seeding rates.
- In "watch", say what the farmer should be able to see in later photos if the mix works, and what would show it does not, so the proposal can be checked.
- Where you are unsure, give a low confidence rather than guessing.
Answer with JSON only:
{"summary": {"text", "confidence"},
 "mix": [{"name": common name, "scientific", "role": one of the roles, "share": e.g. "~30%%", "why": one sentence tied to this field, "confidence"}],
 "sowing": {"text": when and how, "confidence"},
 "cautions": [{"text", "confidence"}],
 "watch": [{"text", "confidence"}]}""" % ", ".join(ROLES)


@dataclass
class Proposal:
    field: str
    date: str
    kind: str = KIND
    model: str = ""
    seeds_on_hand: list[str] = field(default_factory=list)
    notes: list[Observation] = field(default_factory=list)

    @staticmethod
    def path_for(root: Path, field: str, date: str, kind: str = KIND) -> Path:
        return root / PROPOSALS / field / f"{date}-{kind}.md"

    def to_markdown(self) -> str:
        front = {"field": self.field, "date": self.date, "kind": self.kind, "status": "proposal",
                 "model": self.model, "seeds_on_hand": self.seeds_on_hand}
        return notes_to_markdown(front, f"Cover-crop proposal ({self.model or 'none'})", self.notes)

    @classmethod
    def from_markdown(cls, text: str) -> "Proposal":
        front, notes = notes_from_markdown(text)
        return cls(field=front["field"], date=str(front["date"]), kind=front.get("kind", KIND),
                   model=front.get("model", ""), seeds_on_hand=list(front.get("seeds_on_hand") or []), notes=notes)

    def save(self, root: Path) -> Path:
        p = self.path_for(root, self.field, self.date, self.kind)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_markdown(), encoding="utf-8")
        return p


def earlier_proposals(root: Path, field: str, before: str) -> list[Proposal]:
    d = root / PROPOSALS / field
    if not d.exists():
        return []
    return [Proposal.from_markdown(p.read_text(encoding="utf-8"))
            for p in sorted(d.glob(f"*-{KIND}.md")) if p.name < before]


def build_messages(latest: Record, date: str, records_root: Path, seeds_on_hand: list[str] = (),
                   earlier: list[Proposal] = ()) -> list[dict]:
    """Pure apart from reading the note files under records_root. Text only:
    the latest observation already says what the photos showed."""
    obs = "\n".join(o.to_line() for o in latest.observations) or "(no observation yet)"
    parts = [f"Field: {latest.field}. Date: {date}.",
             f"Latest observation ({latest.date}):\n{obs}",
             site_background(records_root),
             notes_for_prompt(records_root, species_in(latest.observations))]
    parts.append("Seeds on hand: " + (", ".join(seeds_on_hand) if seeds_on_hand else "not given; propose from what is commonly sold in <REGION>."))
    wrong = corrected_examples([Record(field=p.field, date=p.date, observations=p.notes) for p in earlier])
    if wrong:
        parts.append("The farmer marked these points of earlier proposals for this field wrong; do not repeat them:\n"
                     + "\n".join(f'- {k}: "{t}" was wrong: {r}' for k, t, r in wrong))
    parts.append("Propose a cover-crop mix for this field now. JSON only.")
    place = Site.load(records_root)
    return [{"role": "system", "content": in_language(place.fill(SYSTEM))},
            {"role": "user", "content": place.fill("\n\n".join(p for p in parts if p))}]


def parse(text: str) -> list[Observation]:
    d = json_value(text)
    out = []
    if d.get("summary"):
        out.append(Observation("summary", d["summary"].get("text", "").strip() + conf(d["summary"])))
    for m in d.get("mix", []):
        role = m.get("role", "other")
        role = role if role in ROLES else "other"
        txt = f"{m.get('name', '?')} ({m.get('scientific', '?')}); role: {role}; share {m.get('share', '?')}; why: {m.get('why', '').strip()}"
        out.append(Observation("mix", txt + conf(m)))
    if d.get("sowing"):
        out.append(Observation("sowing", d["sowing"].get("text", "").strip() + conf(d["sowing"])))
    for key, items in (("caution", d.get("cautions", [])), ("watch", d.get("watch", []))):
        out += [Observation(key, it.get("text", "").strip() + conf(it)) for it in items]
    return out


def propose_cover_crop(latest: Record, date: str, records_root: Path, backend: Backend,
                       seeds_on_hand: list[str] = ()) -> Proposal:
    earlier = earlier_proposals(records_root, latest.field, date)
    text = chat(backend, build_messages(latest, date, records_root, seeds_on_hand, earlier))
    prop = Proposal(field=latest.field, date=date, model=backend.name,
                    seeds_on_hand=list(seeds_on_hand), notes=parse(text))
    prop.save(records_root)
    return prop
