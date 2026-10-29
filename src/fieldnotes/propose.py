"""Propose for one field, from its own records: a cover-crop (green manure)
mix, or where to cut first and how high (the cut proposal, for a plot gone wild).

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
later photos whether it worked. The cut proposal gets the same records plus
the cover and where it comes from (SAM, or the AI's own reading of the photos
when SAM found nothing), and answers with one place and one height to cut
first. Proposals are saved at

    records/_proposals/<field>/<date>-<kind>.md      (kind: cover_crop | cut)

one line per point, so the farmer marks each right or wrong like any other
record, and later observations answer the "watch" lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .concepts import BASE, FieldConcepts
from .describe import site_background
from .llm import Backend, chat, conf, in_language, json_value
from .plants import notes_for_prompt, species_in
from .records import Observation, Record, corrected_examples, notes_from_markdown, notes_to_markdown
from .site import Site

PROPOSALS = "_proposals"
KIND = "cover_crop"
KIND_CUT = "cut"
HEADINGS = {KIND: "Cover-crop proposal", KIND_CUT: "Cut proposal"}
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
        return notes_to_markdown(front, f"{HEADINGS.get(self.kind, self.kind)} ({self.model or 'none'})", self.notes)

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


def earlier_proposals(root: Path, field: str, before: str, kind: str = KIND) -> list[Proposal]:
    d = root / PROPOSALS / field
    if not d.exists():
        return []
    return [Proposal.from_markdown(p.read_text(encoding="utf-8"))
            for p in sorted(d.glob(f"*-{kind}.md")) if p.name < before]


def _context(latest: Record, date: str, records_root: Path) -> list[str]:
    """What both kinds of proposal are given: the latest observation (and what
    the farmer said that day), the site background and the plant notes."""
    obs = "\n".join(o.to_line() for o in latest.observations) or "(no observation yet)"
    parts = [f"Field: {latest.field}. Date: {date}.", f"Latest observation ({latest.date}):\n{obs}"]
    said = [o.to_line() for o in latest.voice if o.verdict != "wrong"]
    if said:
        parts.append("The farmer said that day (work: what they did; seen: what they saw):\n" + "\n".join(said))
    return parts + [site_background(records_root), notes_for_prompt(records_root, species_in(latest.observations))]


def _wrong_part(earlier: list[Proposal]) -> list[str]:
    wrong = corrected_examples([Record(field=p.field, date=p.date, observations=p.notes) for p in earlier])
    if not wrong:
        return []
    return ["The farmer marked these points of earlier proposals for this field wrong; do not repeat them:\n"
            + "\n".join(f'- {k}: "{t}" was wrong: {r}' for k, t, r in wrong)]


def _messages(system: str, parts: list[str], records_root: Path) -> list[dict]:
    place = Site.load(records_root)
    return [{"role": "system", "content": in_language(place.fill(system))},
            {"role": "user", "content": place.fill("\n\n".join(p for p in parts if p))}]


def build_messages(latest: Record, date: str, records_root: Path, seeds_on_hand: list[str] = (),
                   earlier: list[Proposal] = ()) -> list[dict]:
    """Pure apart from reading the note files under records_root. Text only:
    the latest observation already says what the photos showed."""
    parts = _context(latest, date, records_root)
    parts.append("Seeds on hand: " + (", ".join(seeds_on_hand) if seeds_on_hand else "not given; propose from what is commonly sold in <REGION>."))
    parts += _wrong_part(earlier)
    parts.append("Propose a cover-crop mix for this field now. JSON only.")
    return _messages(SYSTEM, parts, records_root)


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


# ---- where to cut first ---------------------------------------------------

CUT_SYSTEM = """You propose where to cut first, and how high, on <FIELD>: a plot left uncut that has grown wild like abandoned farmland.
Everything you know about this plot is below: its latest observation, how much of it each plant covers and where that figure comes from, why its dominant plants dominate, its terrain, geology, soil and surroundings, and the farmer's own knowledge.
Rules:
- Natural farming: no tillage, no pulling of roots, no herbicide. Cut, and lay what is cut on the ground as mulch. The roots and their fungi stay.
- The aim is to bring the plot back into crops step by step, not to clear it. Propose ONE place and ONE height to cut first, not a menu.
- Mind the season in <REGION> at this date: a plant in flower or in seed (cut before it sets seed), tall dry grass, what can regrow or be sown before winter.
- Mind the terrain and the moisture in the site background. The farmer's knowledge there overrides general advice.
- Say what the proposal rests on: the cover from SAM, or only the AI's estimate from the photos when SAM found nothing, and the site facts you used.
- Describe the place so the farmer can find it in the photo (edge, strip width, direction).
- In "watch", say what the next days' photos should show if the cut was right (what regrows first, bare soil, seedlings) and what would show it was wrong.
- Where you are unsure, give a low confidence rather than guessing.
Answer with JSON only:
{"summary": {"text": one sentence: where first, how high, why, "confidence"},
 "basis": {"text", "confidence"},
 "where": {"text", "confidence"},
 "height": {"text": the cutting height and why, "confidence"},
 "leave": [{"text": what not to cut and why, "confidence"}],
 "method": {"text": cut and lay, tool, order, "confidence"},
 "watch": [{"text", "confidence"}],
 "cautions": [{"text", "confidence"}]}"""

CUT_LINES = ("summary", "basis", "where", "height", "leave", "method", "watch", "cautions")


def cover_basis(latest: Record, records_root: Path | None = None) -> str:
    """The cover of the plot and where it comes from: per plant, SAM's share
    when one of its phrases found it, else say plainly that the share is the
    AI's own reading of the photos (the dominant line)."""
    base = {noun for noun, _ in BASE}
    sam = ", ".join(f"{k} {v}%" for k, v in latest.coverage.items()) or "none"
    dominant = "; ".join(o.text for o in latest.observations if o.key == "dominant") or "not given"
    found = {k: v for k, v in latest.coverage.items() if k not in base and v > 0}
    if not found:
        return (f"SAM 3.1 found none of the plants on {latest.date} ({sam}), so there is no measured cover. "
                f"The shares come only from the AI's own reading of the photos: {dominant}. Say so in basis.")
    targets = {c.noun: c.target for c in FieldConcepts.load(records_root, latest.field).items} if records_root else {}
    measured = "; ".join(f'{targets.get(k, k)} by "{k}" {v}%' for k, v in found.items())
    out = (f"Cover measured by SAM 3.1 on {latest.date} (% of the photo each phrase outlined): {sam}. "
           f"Found: {measured}. A phrase for a part (flowers, leaves) measures that part, not the plant's whole share.")
    unmeasured = [f"{n} ({s})" for n, s in species_in([o for o in latest.observations if o.key == "dominant"])
                  if not any(s in targets.get(k, "") for k in found)]
    if targets and unmeasured:
        out += (f" SAM found no phrase for {', '.join(unmeasured)}: their shares come only from the AI's own "
                f"reading of the photos: {dominant}.")
    return out + " Say in basis which numbers SAM measured and which are the AI's reading."


def build_cut_messages(latest: Record, date: str, records_root: Path, earlier: list[Proposal] = ()) -> list[dict]:
    parts = _context(latest, date, records_root) + [cover_basis(latest, records_root)] + _wrong_part(earlier)
    parts.append("Where should the farmer cut first, and how high? JSON only.")
    return _messages(CUT_SYSTEM, parts, records_root)


def parse_cut(text: str) -> list[Observation]:
    d = json_value(text)
    out = []
    for key in CUT_LINES:
        items = d.get(key) or []
        for it in items if isinstance(items, list) else [items]:
            if isinstance(it, dict) and str(it.get("text", "")).strip():
                out.append(Observation("caution" if key == "cautions" else key,
                                       " ".join(str(it["text"]).split()) + conf(it)))
    return out


def propose_cut(latest: Record, date: str, records_root: Path, backend: Backend) -> Proposal:
    earlier = earlier_proposals(records_root, latest.field, date, KIND_CUT)
    text = chat(backend, build_cut_messages(latest, date, records_root, earlier))
    prop = Proposal(field=latest.field, date=date, kind=KIND_CUT, model=backend.name, notes=parse_cut(text))
    prop.save(records_root)
    return prop


def mark(records_root: Path, field: str, date: str, kind: str, key: str, verdict: str | None,
         reason: str | None = None) -> Observation:
    """The farmer's right / wrong on one line of a proposal (`key#2` for the
    second line with that key). A wrong with its reason is the record of a
    rejected proposal, and the next proposal of that kind is told not to repeat it."""
    if verdict not in ("right", "wrong", None):
        raise ValueError(f"verdict must be right or wrong, not {verdict!r}")
    path = Proposal.path_for(records_root, field, date, kind)
    if not path.exists():
        raise FileNotFoundError(f"no {kind} proposal for {field} on {date}")
    prop = Proposal.from_markdown(path.read_text(encoding="utf-8"))
    base, _, nth = key.partition("#")
    lines = [o for o in prop.notes if o.key == base]
    i = int(nth) - 1 if nth.isdigit() else 0
    if not 0 <= i < len(lines):
        raise KeyError(f"no line {key!r} in the {kind} proposal for {field} on {date}")
    line = lines[i]
    line.verdict = verdict
    line.reason = (" ".join(reason.split()) or None) if verdict and reason else None
    prop.save(records_root)
    return line


def propose_cover_crop(latest: Record, date: str, records_root: Path, backend: Backend,
                       seeds_on_hand: list[str] = ()) -> Proposal:
    earlier = earlier_proposals(records_root, latest.field, date)
    text = chat(backend, build_messages(latest, date, records_root, seeds_on_hand, earlier))
    prop = Proposal(field=latest.field, date=date, model=backend.name,
                    seeds_on_hand=list(seeds_on_hand), notes=parse(text))
    prop.save(records_root)
    return prop
