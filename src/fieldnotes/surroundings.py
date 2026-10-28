"""The field's surroundings, from GSI map tiles, read once by the model.

What is around a field matters to it: paddies or orchards next door, the river
and old channels, houses and roads, where weed seed and animals come from, and
how the land was used decades ago. The 国土地理院 (GSI) tile service has, for
the same spot:

    seamlessphoto  current aerial photo
    gazo1          aerial photo 1974-1978
    ort_old10      aerial photo 1961-1969
    std            standard map (roads, buildings, land-use symbols)
    lcmfc2         治水地形分類図 (flood-control landform map: natural levees,
                   old channels, backswamps)

`fetch_maps` stitches a 3x3 block of zoom-16 tiles (about 1.5 km square here)
around the field for each layer, marks the field, and saves the images under
records/surroundings/. `read_surroundings` gives all of them to the model in
one request and writes its reading to records/surroundings.md, one hypothesis
per line, for the farmer to mark right or wrong. site_background() in
describe.py passes that file on to every later judgment.

Source: 国土地理院 地理院タイル (https://maps.gsi.go.jp/development/ichiran.html).
"""

from __future__ import annotations

import io
import math
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from .llm import Backend, chat, conf, json_value
from .records import Observation, notes_from_markdown, notes_to_markdown
from .segment import load_image_as_data_url
from .weather import FIELD_LAT, FIELD_LON

TILE = "https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.{ext}"
LAYERS = {
    "seamlessphoto": ("jpg", "current aerial photo"),
    "gazo1": ("jpg", "aerial photo 1974-1978"),
    "ort_old10": ("png", "aerial photo 1961-1969"),
    "std": ("png", "standard map"),
    "lcmfc2": ("png", "治水地形分類図 (flood-control landform map)"),
}
ATTRIBUTION = "出典: 国土地理院 地理院タイル"
DIR = "surroundings"
ASPECTS = ["land_use", "water", "landform", "history", "seed_source", "animals", "neighbours", "other"]

SYSTEM = """You read the surroundings of one natural-farming field in Tokushima, Japan (no tillage, no fertiliser, no pesticide).
You get several maps of the same area, about 1.5 km square, with the field marked by a red circle in the centre: current and old aerial photos, a standard map, and a flood-control landform map (natural levees, old river channels, backswamps).
Say what in the surroundings is likely to matter to this field: land use next to it and around it (paddies, orchards, other fields, houses, roads, abandoned land), water (river, channels, ditches), the landform it sits on, how land use changed between the 1960s, the 1970s and now, where weed seed and animals may come from, and what neighbours' practices (fertiliser, herbicide, burning) could reach it.
Say only what the maps show or strongly suggest; mark guesses with a low confidence. Name which map each point comes from.
Answer with JSON only: [{"aspect": one of %s, "text": one sentence, "confidence": 0-1}].""" % ASPECTS


def tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    """Web-Mercator tile coordinates (fractional) of a point."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch_mosaic(layer: str, lat: float = FIELD_LAT, lon: float = FIELD_LON, z: int = 16, radius: int = 1) -> Image.Image:
    ext = LAYERS[layer][0]
    fx, fy = tile_xy(lat, lon, z)
    cx, cy = int(fx), int(fy)
    size = 256 * (2 * radius + 1)
    img = Image.new("RGB", (size, size), "white")
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            url = TILE.format(layer=layer, z=z, x=cx + dx, y=cy + dy, ext=ext)
            try:
                with urllib.request.urlopen(url, timeout=20) as r:
                    tile = Image.open(io.BytesIO(r.read())).convert("RGB")
            except Exception:
                continue  # a missing tile stays white
            img.paste(tile, ((dx + radius) * 256, (dy + radius) * 256))
    px = (fx - cx + radius) * 256
    py = (fy - cy + radius) * 256
    ImageDraw.Draw(img).ellipse([px - 14, py - 14, px + 14, py + 14], outline=(255, 0, 0), width=4)
    return img


def fetch_maps(root: Path, layers: list[str] = list(LAYERS)) -> dict[str, Path]:
    out = {}
    d = root / DIR
    d.mkdir(parents=True, exist_ok=True)
    for layer in layers:
        p = d / f"{layer}.jpg"
        if not p.exists():
            fetch_mosaic(layer).save(p, quality=90)
        out[layer] = p
    return out


@dataclass
class Surroundings:
    model: str = ""
    written: str = ""
    maps: list[str] = field(default_factory=list)
    notes: list[Observation] = field(default_factory=list)

    @staticmethod
    def path(root: Path) -> Path:
        return root / "surroundings.md"

    def to_markdown(self) -> str:
        front = {"status": "hypothesis", "model": self.model, "written": self.written,
                 "maps": self.maps, "source": ATTRIBUTION}
        return notes_to_markdown(front, f"Surroundings read from the maps ({self.model or 'none'})", self.notes)

    @classmethod
    def from_markdown(cls, text: str) -> "Surroundings":
        front, notes = notes_from_markdown(text)
        return cls(model=front.get("model", ""), written=str(front.get("written", "")),
                   maps=list(front.get("maps") or []), notes=notes)


def build_messages(maps: dict[str, Path], max_side: int = 768) -> list[dict]:
    content: list[dict] = []
    for layer, p in maps.items():
        content.append({"type": "text", "text": f"--- {LAYERS[layer][1]} ({layer})"})
        url, _, _ = load_image_as_data_url(p, max_side)
        content.append({"type": "image_url", "image_url": {"url": url}})
    content.append({"type": "text", "text": "What around this field is likely to matter to it? JSON only."})
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


def parse(text: str) -> list[Observation]:
    out = []
    for it in json_value(text):
        aspect = it.get("aspect", "other")
        out.append(Observation(key=aspect if aspect in ASPECTS else "other", text=it.get("text", "").strip() + conf(it)))
    return out


def read_surroundings(root: Path, backend: Backend) -> Surroundings:
    maps = fetch_maps(root)
    s = Surroundings(model=backend.name, written=date.today().isoformat(),
                     maps=[str(p.relative_to(root)) for p in maps.values()],
                     notes=parse(chat(backend, build_messages(maps))))
    Surroundings.path(root).write_text(s.to_markdown(), encoding="utf-8")
    return s
