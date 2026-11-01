"""Put what the farmer knows, and what a document says, into records/site.md.

Public maps cannot know that the farmer's mother kept silkworms, or what the
town history says about the village. Those come from the farmer: said in their
own words, or a page of a book photographed. Each becomes one line under a
section of site.md, with its source, so the model reads it as background:

    record  what the farmer said (their words, kept as given)
    data    what a document says, with the document and page as the source

A photographed page is read by the reading model, which copies out only what
concerns the farm's place (its 大字 and town, from lookup), with the numbers as
printed. The photo is kept under records/documents/ and named on each line, so
the farmer can check every line against the page and delete what is wrong.
"""

from __future__ import annotations

import base64
import io
import json
import shutil
from datetime import date
from pathlib import Path

from PIL import Image

from . import llm
from .llm import Backend
from .site import FILE, Site

DOCUMENTS = "documents"
SECTIONS = {"terrain": "Terrain and water", "geology": "Geology and soil", "history": "History of the land",
            "works": "What the farmer knows works here (and what does not)"}
SIDE = 2048  # a printed page needs more pixels than a field photo
HOW_TO = "## How a hypothesis is checked"  # describe.SITE_CHECK_HEADING; everything after it stays out of the prompt

PAGE_PROMPT = """This is a photo of a page from a document the farmer has: {source}.
The farm is in {place}. Copy out every statement on the page about this place
(and about the town or village it is in), above all the land, soil, water, floods,
crops, and how the land was used, with years and numbers exactly as printed.
Write each in the page's own language, close to its wording; do not explain,
interpret or add anything that is not printed. If a table, name its title,
the row and the column. Skip what is about other places.
Answer JSON only: {{"lines": ["...", "..."]}} ({{"lines": []}} if nothing concerns the place)."""


def _sentence(text: str) -> str:
    """One line, ended the way its language ends a sentence."""
    text = " ".join(str(text).split()).rstrip("。.")
    return text + ("。" if text and not text[-1].isascii() else ".")


def line(text: str, source: str | None, day: date) -> str:
    """The farmer's words are a `record`; a document's statement is `data` with the document named."""
    text = _sentence(text)
    if source:
        return f"- `data` {text} — {source}; noted {day.isoformat()}."
    return f"- `record` {text} — the farmer, {day.isoformat()}."


def add(records_root: Path, section: str, lines: list[str]) -> Path:
    """Append lines at the end of a section of site.md (the section is made if missing)."""
    path = records_root / FILE
    if not path.exists():
        raise FileNotFoundError("no records/site.md yet (fieldnotes init)")
    heading = f"## {SECTIONS.get(section, section)}"
    rows = path.read_text(encoding="utf-8").split("\n")
    if heading not in rows:  # a new section goes before the how-to, which the model is not given
        at = rows.index(HOW_TO) if HOW_TO in rows else len(rows)
        while at > 0 and rows[at - 1] == "":
            at -= 1
        rows[at:at] = ["", heading]
    start = rows.index(heading) + 1
    end = next((i for i in range(start, len(rows)) if rows[i].startswith("## ")), len(rows))
    at = end
    while at > start and rows[at - 1] == "":
        at -= 1
    new = list(lines)
    if at == start:  # an empty section: a blank line after the heading
        new.insert(0, "")
    if at == end and end < len(rows):  # no blank line before the next heading yet
        new.append("")
    rows[at:at] = new
    path.write_text("\n".join(rows).rstrip("\n") + "\n", encoding="utf-8")
    return path


def place_name(records_root: Path) -> str:
    """The 大字 and town from lookup's address, else the place in site.md."""
    raw = records_root / "lookup" / "address_jp.json"
    if raw.exists():
        a = json.loads(raw.read_text(encoding="utf-8"))
        town = (a.get("muni") or "").split(",")
        name = " ".join(x for x in (town[3] if len(town) > 3 else "", (a.get("results") or {}).get("lv01Nm", "")) if x)
        if name:
            return name
    return Site.load(records_root).region()


def _data_url(path: Path) -> str:
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((SIDE, SIDE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def read_page(records_root: Path, photo: Path, source: str, day: date, backend: Backend | None = None) -> list[str]:
    """Keep the page photo under records/documents/ and return the lines the model copied from it."""
    docs = records_root / DOCUMENTS
    docs.mkdir(parents=True, exist_ok=True)
    kept = docs / f"{day.isoformat()}-{photo.name}"
    if photo.resolve() != kept.resolve():
        shutil.copyfile(photo, kept)
    prompt = PAGE_PROMPT.format(source=source, place=place_name(records_root))
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt},
                                             {"type": "image_url", "image_url": {"url": _data_url(kept)}}]}]
    backend = backend or Backend.default()
    got = llm.json_value(llm.chat(backend, messages)).get("lines") or []
    by = backend.model
    return [f"- `data` {_sentence(t)} — {source}; read from the farmer's photo of the page "
            f"by {by} (check against the page), {DOCUMENTS}/{kept.name}, {day.isoformat()}." for t in got if str(t).strip()]
