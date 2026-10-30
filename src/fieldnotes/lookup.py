"""Public data about the farm's ground and history, looked up from its coordinates.

The farmer should not have to know where geology or history is kept. For any
farm with lat/lon in records/site.md, `lookup` asks open services that cover
the whole world and writes what they say to records/lookup.md, one `data` or
`reference` line each, with the source URL, so the farmer and the model can
tell where every line came from:

    elevation   Open-Meteo elevation API (Copernicus DEM, 90 m)
    geology     Macrostrat geologic map units (CC BY 4.0; world maps are coarse)
                and, in Japan, the GSJ 20万分の1日本シームレス地質図 V2 legend API
    soil        ISRIC SoilGrids 2.0 (pH, organic carbon, clay, sand; 250 m model;
                no value where the map is masked, e.g. built-up land)
    Japan       国土地理院 (address, 1 m elevation, landform, active faults), the
                ハザードマップポータルサイト (sediment-disaster and flood zones) and the
                産総研 catalogue (the 1:50,000 sheet and its report): lookup_jp.py
    history     Wikipedia articles with coordinates near the farm (in the
                country's language) and OpenStreetMap features tagged
                `historic` (castles, archaeological sites, flood memorials ...)

`search(words)` looks for any name near the farm in the same two places
(Wikipedia full text, OpenStreetMap names), for the farmer's own questions:
"was there a castle here?".

Raw answers are kept under records/lookup/ so the file can be rebuilt and
checked later. Nothing here is a judgment: the model reads these lines as
background, and the farmer marks or corrects them like any other.
"""

from __future__ import annotations

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from . import lookup_jp
from .site import Site

USER_AGENT = "fieldnotes/0.1 (+https://github.com/aiseed-dev/fieldnotes)"
FILE = "lookup.md"
RAW = "lookup"
RADIUS_M = 3000  # history and search: features within this distance
WIKI_RADIUS_M = 5000
WIKI_LANG = {"JP": "ja", "FR": "fr", "DE": "de", "ES": "es", "IT": "it", "PT": "pt", "BR": "pt",
             "CN": "zh", "TW": "zh", "KR": "ko", "NL": "nl", "MX": "es", "AR": "es", "CO": "es"}
SOIL = {"phh2o": ("pH (water)", 10, ""), "soc": ("organic carbon", 10, " g/kg"),
        "clay": ("clay", 10, " %"), "sand": ("sand", 10, " %")}
OVERPASS = "https://overpass-api.de/api/interpreter"


def get_json(url: str, data: dict | None = None, timeout: float = 60, tries: int = 3):
    """GET (or POST form data) and parse JSON; the one place that touches the
    network. Busy answers (429, 5xx; Overpass often) are retried after a pause."""
    body = urllib.parse.urlencode(data).encode() if data else None
    for i in range(tries):
        req = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500 or i == tries - 1:
                raise
            time.sleep(10 * (i + 1))


def _url(base: str, **q) -> str:
    return base + "?" + urllib.parse.urlencode(q)


def _wiki(lang: str, tries: int = 3, **q):
    """The MediaWiki API answers "too busy" as JSON with an error, not as 429."""
    for i in range(tries):
        raw = get_json(_url(f"https://{lang}.wikipedia.org/w/api.php", format="json", **q))
        if "error" not in raw:
            return raw
        if i < tries - 1:
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"Wikipedia: {raw['error'].get('code')}")


def _km(lat1, lon1, lat2, lon2) -> float:
    dy = (lat2 - lat1) * 111.2
    dx = (lon2 - lon1) * 111.2 * math.cos(math.radians(lat1))
    return math.hypot(dx, dy)


def _direction(lat1, lon1, lat2, lon2) -> str:
    angle = math.degrees(math.atan2((lon2 - lon1) * math.cos(math.radians(lat1)), lat2 - lat1)) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((angle + 22.5) // 45) % 8]


def wiki_lang(site: Site) -> str:
    return WIKI_LANG.get(site.country, "en")


# ---- each source: (lines, raw answer) -----------------------------------

def elevation(site: Site):
    url = _url("https://api.open-meteo.com/v1/elevation", latitude=site.lat, longitude=site.lon)
    raw = get_json(url)
    return [f"- `data` Elevation {raw['elevation'][0]:g} m. — Open-Meteo elevation API (Copernicus DEM), {url}"], raw


def geology_world(site: Site):
    url = _url("https://macrostrat.org/api/v2/geologic_units/map", lat=site.lat, lng=site.lon)
    raw = get_json(url)
    lines = []
    for u in raw.get("success", {}).get("data", []):
        what = "; ".join(x for x in (u.get("name"), u.get("lith"), u.get("descrip")) if x)
        age = u.get("b_int_name") if u.get("b_int_name") == u.get("t_int_name") else \
            f"{u.get('b_int_name')} to {u.get('t_int_name')}"
        lines.append(f"- `data` Bedrock: {what or 'unnamed unit'} ({age}; map scale {u.get('scale')}). "
                     f"— Macrostrat (CC BY 4.0), {url}")
    return lines, raw


def geology_japan(site: Site):
    url = f"https://gbank.gsj.jp/seamless/v2/api/1.2/legend.json?point={site.lat},{site.lon}"
    raw = get_json(url)
    parts = [raw.get(k) for k in ("formationAge_ja", "group_ja", "lithology_ja") if raw.get(k)]
    if not parts:
        return [], raw
    return [f"- `data` 地質（シームレス地質図 V2）: {' / '.join(parts)}。 — 産総研 地質調査総合センター, {url}"], raw


def soil(site: Site):
    q = [("lon", site.lon), ("lat", site.lat), *[("property", p) for p in SOIL],
         ("depth", "0-5cm"), ("depth", "15-30cm"), ("value", "mean")]
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query?" + urllib.parse.urlencode(q)
    raw = get_json(url)
    lines = []
    for layer in raw.get("properties", {}).get("layers", []):
        label, factor, unit = SOIL.get(layer["name"], (layer["name"], 1, ""))
        vals = [(d["label"], d["values"].get("mean")) for d in layer.get("depths", [])]
        got = [f"{lab} {v / factor:g}{unit}" for lab, v in vals if v is not None]
        if got:
            lines.append(f"- `data` Soil {label}: {', '.join(got)} (modelled, 250 m). — ISRIC SoilGrids 2.0, {url}")
    if not lines:
        lines.append(f"- `data` SoilGrids has no value at this point (masked, e.g. built-up land). — {url}")
    return lines, raw


def wiki_nearby(site: Site):
    lang = wiki_lang(site)
    raw = _wiki(lang, action="query", list="geosearch", gscoord=f"{site.lat}|{site.lon}",
                gsradius=WIKI_RADIUS_M, gslimit=30)
    lines = []
    for g in raw.get("query", {}).get("geosearch", []):
        link = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(g['title'].replace(' ', '_'))}"
        where = f"{g['dist'] / 1000:.1f} km {_direction(site.lat, site.lon, g['lat'], g['lon'])}"
        lines.append(f"- `reference` {g['title']} ({where}). — Wikipedia, {link}")
    return lines, raw


def _overpass(query: str):
    return get_json(OVERPASS, {"data": f"[out:json][timeout:50];{query}out tags center 80;"}, timeout=90)


def _osm_lines(site: Site, elements: list[dict]) -> list[str]:
    lines = []
    for e in elements:
        t = e.get("tags", {})
        name = t.get("name") or t.get("name:en")
        if not name:
            continue
        c = e.get("center") or {"lat": e.get("lat"), "lon": e.get("lon")}
        kind = t.get("historic") or t.get("waterway") or t.get("place") or "feature"
        extra = "; ".join(f"{k}: {t[k]}" for k in ("hazard:name", "start_date", "wikipedia") if t.get(k))
        where = f"{_km(site.lat, site.lon, c['lat'], c['lon']):.1f} km {_direction(site.lat, site.lon, c['lat'], c['lon'])}"
        link = f"https://www.openstreetmap.org/{e['type']}/{e['id']}"
        lines.append(f"- `reference` {name} ({kind}, {where}{'; ' + extra if extra else ''}). "
                     f"— OpenStreetMap (ODbL), {link}")
    return list(dict.fromkeys(lines))


def history_osm(site: Site):
    raw = _overpass(f"nwr(around:{RADIUS_M},{site.lat},{site.lon})[historic];")
    return _osm_lines(site, raw.get("elements", [])), raw


NAMES = {"elevation": "Open-Meteo elevation", "geology": "Macrostrat", "geology_jp": "GSJ シームレス地質図",
         "soil": "ISRIC SoilGrids", "wikipedia": "Wikipedia", "historic": "OpenStreetMap",
         "address_jp": "国土地理院 逆ジオコーダ", "elevation_jp": "国土地理院 標高API",
         "landform_jp": "国土地理院 地形分類", "faults_jp": "国土地理院 活断層図",
         "hazard_jp": "ハザードマップポータルサイト", "sheet_jp": "産総研 地質図カタログ",
         "soil_jp": "日本土壌インベントリー"}
SOURCES = {"address_jp": lookup_jp.address, "elevation_jp": lookup_jp.elevation, "elevation": elevation,
           "landform_jp": lookup_jp.landform, "geology": geology_world, "geology_jp": geology_japan,
           "sheet_jp": lookup_jp.sheet,
           "faults_jp": lookup_jp.faults, "hazard_jp": lookup_jp.hazards,
           "soil": soil, "soil_jp": lookup_jp.soil_hint, "wikipedia": wiki_nearby, "historic": history_osm}
JAPAN_ONLY = {k for k in SOURCES if k.endswith("_jp")}
SECTIONS = [("Place", ["address_jp"]), ("Terrain", ["elevation_jp", "elevation", "landform_jp"]),
            ("Geology", ["geology_jp", "sheet_jp", "geology"]), ("Faults and hazards", ["faults_jp", "hazard_jp"]),
            ("Soil", ["soil", "soil_jp"]), ("History and places nearby", ["historic", "wikipedia"])]


def lookup(records_root: Path) -> Path:
    """Ask every source, keep the raw answers, write records/lookup.md.
    A source that fails (down, in maintenance) is named in the file, not fatal."""
    site = Site.load(records_root)
    if not site.located:
        raise ValueError("no lat/lon in records/site.md (fieldnotes init)")
    raw_dir = records_root / RAW
    raw_dir.mkdir(parents=True, exist_ok=True)
    got: dict[str, list[str]] = {}
    for key, fn in SOURCES.items():
        if key in JAPAN_ONLY and site.country != "JP":
            continue
        try:
            lines, raw = fn(site)
            (raw_dir / f"{key}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
            got[key] = lines
        except Exception as e:  # noqa: BLE001 - a missing source should not lose the others
            got[key] = [f"- ({NAMES[key]}: not reached on {date.today()}, {e if isinstance(e, RuntimeError) else type(e).__name__}; run lookup again later)"]
    out = ["---", f"place: {site.place}", f"lat: {site.lat}", f"lon: {site.lon}",
           f"fetched: {date.today().isoformat()}", "---", "",
           "# Public data looked up for this farm", "",
           "Fetched from open services by `fieldnotes lookup`; raw answers in records/lookup/.",
           "`data` lines are measurements or maps (world maps are coarse); `reference` lines are",
           "places with a name near the farm, worth reading about. Mark or correct them like any other line.", ""]
    for title, keys in SECTIONS:
        lines = [x for k in keys for x in got.get(k, [])]
        if lines:
            out += [f"## {title}", "", *lines, ""]
    path = records_root / FILE
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def search(records_root: Path, words: str, radius_m: int = 10000) -> list[str]:
    """Look for `words` near the farm: Wikipedia full text (country's language,
    articles with coordinates within radius_m; anywhere if the farm has none)
    and OpenStreetMap names within radius_m. Returns reference lines."""
    site = Site.load(records_root)
    lang = wiki_lang(site)
    out = []
    near = f" nearcoord:{radius_m // 1000}km,{site.lat},{site.lon}" if site.located else ""
    raw = _wiki(lang, action="query", list="search", srsearch=words + near, srlimit=10)
    for r in raw.get("query", {}).get("search", []):
        link = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(r['title'].replace(' ', '_'))}"
        out.append(f"- `reference` {r['title']}. — Wikipedia, {link}")
    if site.located:
        name = words.replace('"', "")
        raw = _overpass(f'nwr(around:{radius_m},{site.lat},{site.lon})["name"~"{name}"];')
        out += _osm_lines(site, raw.get("elements", []))
    return out
