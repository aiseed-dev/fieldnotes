"""The field's surroundings, from map tiles, read once by the model.

What is around a field matters to it: paddies or orchards next door, the river
and old channels, houses and roads, where weed seed and animals come from, and
how the land was used decades ago. In Japan the 国土地理院 (GSI) tile service
has, for the same spot:

    seamlessphoto  current aerial photo
    gazo1          aerial photo 1974-1978
    ort_old10      aerial photo 1961-1969
    std            standard map (roads, buildings, land-use symbols)
    lcmfc2         治水地形分類図 (flood-control landform map: natural levees,
                   old channels, backswamps)

Elsewhere only the OpenStreetMap standard map is used (tile.openstreetmap.org,
fetched once when the farmer asks, with this app's User-Agent, as the OSMF
tile policy asks). The farm's place and country come from records/site.md.

`fetch_maps` stitches a 3x3 block of zoom-16 tiles (about 1.5 km square here)
around the field for each layer, marks the field, and saves the images under
records/surroundings/. `read_surroundings` gives all of them to the model in
one request and writes its reading to records/surroundings.md, one hypothesis
per line, for the farmer to mark right or wrong. site_background() in
describe.py passes that file on to every later judgment.

Sources: 国土地理院 地理院タイル (https://maps.gsi.go.jp/development/ichiran.html);
OpenStreetMap tile usage policy (https://operations.osmfoundation.org/policies/tiles/).
"""

from __future__ import annotations

import io
import math
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from .llm import Backend, chat, conf, in_language, json_value
from .records import Observation, notes_from_markdown, notes_to_markdown
from .segment import load_image_as_data_url
from .site import Site

GSI = "https://cyberjapandata.gsi.go.jp/xyz/{layer}/{z}/{x}/{y}.{ext}"
OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = "fieldnotes/0.1 (+https://github.com/aiseed-dev/fieldnotes)"
LAYERS = {
    "seamlessphoto": ("jpg", "current aerial photo"),
    "gazo1": ("jpg", "aerial photo 1974-1978"),
    "ort_old10": ("png", "aerial photo 1961-1969"),
    "std": ("png", "standard map"),
    "lcmfc2": ("png", "治水地形分類図 (flood-control landform map)"),
    "osm": ("png", "OpenStreetMap standard map"),
}
JAPAN = ["seamlessphoto", "gazo1", "ort_old10", "std", "lcmfc2"]
ATTRIBUTION = {"gsi": "出典: 国土地理院 地理院タイル", "osm": "© OpenStreetMap contributors"}
DIR = "surroundings"
ASPECTS = ["land_use", "water", "landform", "history", "seed_source", "animals", "neighbours", "other"]

SYSTEM = """You read the surroundings of <FIELD>.
You get one or more maps of the same area, about 1.5 km square, with the field marked by a red circle in the centre (each map is named: aerial photos of now and of decades ago, standard maps, landform maps), as far as they exist for this place.
Say what in the surroundings is likely to matter to this field: land use next to it and around it (paddies, orchards, other fields, houses, roads, abandoned land), water (river, channels, ditches), the landform it sits on, how land use changed between the 1960s, the 1970s and now, where weed seed and animals may come from, and what neighbours' practices (fertiliser, herbicide, burning) could reach it.
Say only what the maps show or strongly suggest; mark guesses with a low confidence. Name which map each point comes from.
Answer with JSON only: [{"aspect": one of %s, "text": one sentence, "confidence": 0-1}].""" % ASPECTS


def tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    """Web-Mercator tile coordinates (fractional) of a point."""
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def layers_for(site: Site) -> list[str]:
    return JAPAN if site.country == "JP" else ["osm"]


def attribution(layers) -> str:
    return "; ".join(dict.fromkeys(ATTRIBUTION["osm" if layer == "osm" else "gsi"] for layer in layers))


def fetch_mosaic(layer: str, lat: float, lon: float, z: int = 16, radius: int = 1) -> Image.Image:
    ext = LAYERS[layer][0]
    fx, fy = tile_xy(lat, lon, z)
    cx, cy = int(fx), int(fy)
    size = 256 * (2 * radius + 1)
    img = Image.new("RGB", (size, size), "white")
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            url = (OSM if layer == "osm" else GSI).format(layer=layer, z=z, x=cx + dx, y=cy + dy, ext=ext)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=20) as r:
                    tile = Image.open(io.BytesIO(r.read())).convert("RGB")
            except Exception:
                continue  # a missing tile stays white
            img.paste(tile, ((dx + radius) * 256, (dy + radius) * 256))
    px = (fx - cx + radius) * 256
    py = (fy - cy + radius) * 256
    ImageDraw.Draw(img).ellipse([px - 14, py - 14, px + 14, py + 14], outline=(255, 0, 0), width=4)
    return img


def fetch_maps(root: Path, layers: list[str] | None = None) -> dict[str, Path]:
    site = Site.load(root)
    if not site.located:
        raise ValueError("no lat/lon in records/site.md (fieldnotes init)")
    layers = layers or layers_for(site)
    out = {}
    d = root / DIR
    d.mkdir(parents=True, exist_ok=True)
    for layer in layers:
        p = d / f"{layer}.jpg"
        if not p.exists():
            fetch_mosaic(layer, site.lat, site.lon).save(p, quality=90)
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
                 "maps": self.maps, "source": attribution(Path(m).stem for m in self.maps)}
        return notes_to_markdown(front, f"Surroundings read from the maps ({self.model or 'none'})", self.notes)

    @classmethod
    def from_markdown(cls, text: str) -> "Surroundings":
        front, notes = notes_from_markdown(text)
        return cls(model=front.get("model", ""), written=str(front.get("written", "")),
                   maps=list(front.get("maps") or []), notes=notes)


def build_messages(maps: dict[str, Path], max_side: int = 768, place: Site | None = None) -> list[dict]:
    content: list[dict] = []
    for layer, p in maps.items():
        content.append({"type": "text", "text": f"--- {LAYERS[layer][1]} ({layer})"})
        url, _, _ = load_image_as_data_url(p, max_side)
        content.append({"type": "image_url", "image_url": {"url": url}})
    content.append({"type": "text", "text": "What around this field is likely to matter to it? JSON only."})
    return [{"role": "system", "content": in_language((place or Site()).fill(SYSTEM))}, {"role": "user", "content": content}]


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
                     notes=parse(chat(backend, build_messages(maps, place=Site.load(root)))))
    Surroundings.path(root).write_text(s.to_markdown(), encoding="utf-8")
    return s
