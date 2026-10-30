"""Japanese primary data for `lookup`: 国土地理院 and the ハザードマップポータルサイト.

The world sources in lookup.py are coarse in Japan (Macrostrat's world map
called the Izumi Group under 新居浜市萩生 an intrusive rock; SoilGrids is
masked over farmland next to houses). These come from the coordinates alone
and settle the place:

    address_jp    国土地理院 逆ジオコーダ → 大字 (and 市区町村 from muni.js)
    elevation_jp  国土地理院 標高API → elevation, and which DEM (1 m laser where flown)
    landform_jp   国土地理院 ベクトルタイル「地形分類」(z14 GeoJSON) → the class of the
                  polygon the point is in (natural landform; artificial one if any)
    faults_jp     国土地理院 活断層図 (afm, scanned raster) → distance and direction to
                  the nearest active fault line, and to the nearest on the other side
                  (within 2 km at z15; if none, within 4 km at z14)
    hazard_jp     ハザードマップポータルサイト raster tiles → inside or outside, and the
                  distance to, 土砂災害警戒区域 and 洪水浸水想定区域 (想定最大規模)
    sheet_jp      産総研 地質図カタログ (5万分の1地質図幅) → the sheet the point is on,
                  and its report: the report's text says what the deposits are made of

Each returns (lines, raw) like the sources in lookup.py. A tile that is not
there (404) means the layer has nothing in it; any other failure raises, and
lookup writes its "not reached" line.
"""

from __future__ import annotations

import io
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

from .site import Site

TIMEOUT = 10  # a slow tile server must not stall init
GSI = "https://cyberjapandata.gsi.go.jp/xyz"
PORTAL = "https://disaportaldata.gsi.go.jp/raster"
EARTH_M = 40075016.686

# ベクトルタイル「地形分類」: code → (class, 土地条件図 / 治水地形分類図 name).
# From 国土地理院「ベクトルタイル「地形分類」の凡例対応表」
# https://www.gsi.go.jp/bousaichiri/bousaichiri41017.html (read 2026-10-30).
LANDFORM = {
    "10101": ("山地斜面等", "斜面（山地）"), "11201": ("山地斜面等", "火砕丘"), "11202": ("山地斜面等", "溶岩円頂丘"),
    "11203": ("山地斜面等", "火口"), "11204": ("山地斜面等", "溶岩流地形"), "1010101": ("山地斜面等", "山地"),
    "10202": ("崖・段丘崖", "崖"), "10204": ("崖・段丘崖", "禿しゃ地・露岩"), "2010201": ("崖・段丘崖", "崖（段丘崖）"),
    "10205": ("地すべり地形", "地すべり（滑落崖）"), "10206": ("地すべり地形", "地すべり（移動体）"),
    "10301": ("台地・段丘", "高位面"), "10302": ("台地・段丘", "上位面"), "10303": ("台地・段丘", "中位面"),
    "10304": ("台地・段丘", "下位面"), "10305": ("台地・段丘", "完新世段丘・低位面"), "10306": ("台地・段丘", "台地・段丘"),
    "10307": ("台地・段丘", "対比困難な段丘"), "10308": ("台地・段丘", "洪積台地"), "10310": ("台地・段丘", "岩石台地"),
    "10312": ("台地・段丘", "溶岩台地"), "10314": ("台地・段丘", "更新世段丘"), "10508": ("台地・段丘", "台地・段丘状の地形"),
    "2010101": ("台地・段丘", "段丘面"),
    "10401": ("山麓堆積地形", "麓屑面"), "10402": ("山麓堆積地形", "崖錐"), "10403": ("山麓堆積地形", "土石流堆"),
    "10404": ("山麓堆積地形", "土石流段丘"), "10406": ("山麓堆積地形", "山麓堆積地形"),
    "10407": ("山麓堆積地形", "崖錐・麓屑面・土石流堆"), "3010101": ("山麓堆積地形", "山麓堆積地形"),
    "10501": ("扇状地", "扇状地"), "10502": ("扇状地", "緩扇状地"), "3020101": ("扇状地", "扇状地"),
    "10503": ("自然堤防", "自然堤防"), "3040101": ("自然堤防", "微高地（自然堤防）"),
    "10506": ("天井川等", "天井川沿いの微高地"), "10507": ("天井川等", "旧天井川の微高地"), "10801": ("天井川等", "天井川の部分"),
    "10504": ("砂州・砂丘", "砂丘"), "10505": ("砂州・砂丘", "砂（礫）堆・州"), "10512": ("砂州・砂丘", "砂州・砂堆・砂丘"),
    "3050101": ("砂州・砂丘", "砂州・砂丘"),
    "10601": ("凹地・浅い谷", "凹地・浅い谷"), "2010301": ("凹地・浅い谷", "浅い谷"),
    "10701": ("氾濫平野・海岸平野", "谷底平野・氾濫平野"), "10702": ("氾濫平野・海岸平野", "海岸平野・三角州"),
    "10705": ("氾濫平野・海岸平野", "湖岸平野・三角州"), "3030101": ("氾濫平野・海岸平野", "氾濫平野"),
    "10703": ("後背低地・湿地", "後背低地"), "10804": ("後背低地・湿地", "湿地"), "3030201": ("後背低地・湿地", "後背湿地"),
    "10704": ("旧河道", "旧河道"), "3040201": ("旧河道", "旧河道（明瞭）"), "3040202": ("旧河道", "旧河道（不明瞭）"),
    "3040301": ("落堀", "落堀"),
    "10802": ("河川敷・浜", "高水敷"), "10803": ("河川敷・浜", "低水敷・浜"), "10807": ("河川敷・浜", "低水敷・浜・潮汐平野"),
    "10808": ("河川敷・浜", "高水敷・低水敷・浜"),
    "10805": ("水部", "落堀"), "10806": ("水部", "潮汐平野"), "10901": ("水部", "水部"),
    "10903": ("水部", "河川・水涯線及び水面"), "5010201": ("水部", "現河道・水面"),
    "10904": ("旧水部", "旧水部"), "5010301": ("旧水部", "旧水部"),
    "11001": ("切土地", "切土地・平坦化地"), "11003": ("切土地", "切土斜面"), "11009": ("切土地", "凹陥地"),
    "11011": ("切土地", "切土地"), "4010301": ("切土地", "切土地"),
    "11002": ("農耕平坦化地", "農耕平坦化地"), "11008": ("干拓地", "干拓地"), "4010101": ("干拓地", "干拓地"),
    "11004": ("盛土地・埋立地", "盛土斜面"), "11005": ("盛土地・埋立地", "高い盛土地"), "11006": ("盛土地・埋立地", "盛土地"),
    "11007": ("盛土地・埋立地", "埋土地"), "11014": ("盛土地・埋立地", "盛土地・埋立地"),
    "4010201": ("盛土地・埋立地", "盛土地・埋立地"), "11010": ("改変工事中", "改変工事中"),
}
LANDFORM_LAYERS = [("experimental_landformclassification1", "natural"), ("experimental_landformclassification2", "artificial")]

# ハザードマップポータルサイト raster layers: (key, name). 土砂災害警戒区域 is three layers.
SEDIMENT = [("05_dosekiryukeikaikuiki", "土石流"), ("05_kyukeishakeikaikuiki", "急傾斜地の崩壊"),
            ("05_jisuberikeikaikuiki", "地すべり")]
FLOOD = "01_flood_l2_shinsuishin_data"
FAULT_SEARCH = [(15, 2), (14, 2)]  # 5×5 tiles: at least 2 km round the point at z15 (~4 m px), then 4 km at z14
HAZARD_Z, HAZARD_R = 15, 1  # 3×3 tiles: at least 1 km

# 産総研 地質図カタログ, 5万分の1地質図幅: one page per region, each with an index map
# whose rectangles are the sheets (15′ of longitude by 10′ of latitude) on a regular
# pixel grid. Per page: (west longitude of the grid, its north edge in 10′ steps,
# pixel x and y of that corner, columns, rows). Placed by the sheets named after
# towns (国土地理院 地名検索, 2026-10-30). Pages 9 and 16 (islands) are not on one grid.
CATALOGUE = "https://www.gsj.jp/Map/JP/geology4-{}.html"
SHEET_PX = (41.6, 34.2)
SHEET_GRID = {
    1: (142.5, 271, 94, 118, 12, 10), 2: (142.5, 261, 94, 80, 14, 10), 3: (141.0, 274, 258, 15, 7, 13),
    4: (139.25, 261, 15, 34, 13, 13), 5: (139.5, 250, 130, 104, 10, 10), 6: (139.0, 240, 151, 55, 13, 12),
    7: (138.0, 230, 78, 70, 13, 11), 8: (138.0, 219, 125, 58, 12, 12), 10: (135.0, 227, 86, 4, 12, 14),
    11: (135.0, 213, 120, 35, 12, 13), 12: (132.0, 218, 119, 45, 12, 11), 13: (132.0, 207, 119, 61, 12, 11),
    14: (129.0, 209, 118, 70, 12, 11), 15: (128.25, 200, 37, 13, 15, 14),
}


def get_bytes(url: str) -> bytes | None:
    """The one place that touches the network here; None when the tile is not there (404)."""
    req = urllib.request.Request(url, headers={"User-Agent": "fieldnotes/0.1 (+https://github.com/aiseed-dev/fieldnotes)"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _json(url: str):
    import json
    data = get_bytes(url)
    return json.loads(data.decode("utf-8")) if data is not None else None


# ---- geometry -------------------------------------------------------------

def tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    """The point in tile coordinates (fractional) at zoom z."""
    n = 2 ** z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def metres_per_px(lat: float, z: int) -> float:
    return EARTH_M * math.cos(math.radians(lat)) / 2 ** z / 256


def bearing(east: float, north: float) -> str:
    angle = math.degrees(math.atan2(east, north)) % 360
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((angle + 22.5) // 45) % 8]


def distance(m: float) -> str:
    return f"{round(m, -1):.0f} m" if m < 1000 else f"{m / 1000:.1f} km"


def _inside(x: float, y: float, ring: list) -> bool:
    c = False
    for i in range(len(ring)):
        x1, y1 = ring[i][:2]
        x2, y2 = ring[i - 1][:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def polygon_at(features: list[dict], lon: float, lat: float) -> dict | None:
    """The first (Multi)Polygon feature the point is in, holes respected."""
    for f in features:
        g = f.get("geometry") or {}
        polys = [g["coordinates"]] if g.get("type") == "Polygon" else g.get("coordinates", []) \
            if g.get("type") == "MultiPolygon" else []
        for rings in polys:
            if rings and _inside(lon, lat, rings[0]) and not any(_inside(lon, lat, h) for h in rings[1:]):
                return f
    return None


def nearest(mask: np.ndarray, px: float, py: float, m_px: float) -> list[tuple[float, str, np.ndarray]]:
    """(metres, direction, vector) to the nearest True pixel of `mask` from (px, py),
    then to the nearest one on the other side (more than 90° away), if any. Only
    pixels within the circle the mosaic covers in every direction count: one
    further out, in a corner, may not be the nearest."""
    ys, xs = np.nonzero(mask)
    v = np.stack([xs + 0.5 - px, py - (ys + 0.5)], axis=1)  # (east, north) in px
    d = np.hypot(v[:, 0], v[:, 1])
    keep = d <= min(px, py, mask.shape[1] - px, mask.shape[0] - py)
    v, d = v[keep], d[keep]
    if not len(d):
        return []
    i = int(d.argmin())
    out = [(float(d[i]) * m_px, bearing(*v[i]), v[i])]
    other = v @ v[i] < 0
    if other.any():
        j = int(np.where(other, d, np.inf).argmin())
        out.append((float(d[j]) * m_px, bearing(*v[j]), v[j]))
    return out


def _mosaic(urls: dict[tuple[int, int], str], classify) -> tuple[np.ndarray, list[str]]:
    """Fetch the tiles (in parallel) and paste classify(tile) masks into one array;
    a missing tile (404) is all False. Returns (mask, URLs that answered)."""
    xs = sorted({x for x, _ in urls})
    ys = sorted({y for _, y in urls})
    mask = np.zeros((len(ys) * 256, len(xs) * 256), dtype=bool)
    with ThreadPoolExecutor(8) as pool:
        got = dict(zip(urls, pool.map(get_bytes, urls.values())))
    seen = []
    for (x, y), data in got.items():
        if data is None:
            continue
        seen.append(urls[(x, y)])
        tile = np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))
        r, c = ys.index(y) * 256, xs.index(x) * 256
        mask[r:r + 256, c:c + 256] = classify(tile)
    return mask, seen


def _around(lat: float, lon: float, z: int, radius: int, url) -> tuple[dict, float, float]:
    fx, fy = tile_xy(lat, lon, z)
    cx, cy = int(fx), int(fy)
    urls = {(cx + dx, cy + dy): url(z, cx + dx, cy + dy) for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)}
    return urls, (fx - cx + radius) * 256, (fy - cy + radius) * 256


def red_lines(tile: np.ndarray) -> np.ndarray:
    """Fault lines on the scanned 活断層図: saturated red, kept only where a few
    red pixels touch (scan noise and orange landform areas are not red enough)."""
    r, g, b = (tile[..., i].astype(int) for i in range(3))
    red = (r > 170) & (g < 80) & (b < 80) & (r - g > 110)
    n = sum(np.roll(np.roll(red, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    return red & (n >= 3)


def painted(tile: np.ndarray) -> np.ndarray:
    return tile[..., 3] > 0


# ---- the sources ----------------------------------------------------------

def address(site: Site):
    url = "https://mreversegeocoder.gsi.go.jp/reverse-geocoder/LonLatToAddress?" + \
          urllib.parse.urlencode({"lat": site.lat, "lon": site.lon})
    raw = _json(url) or {}
    res = raw.get("results") or {}
    if not res:
        return [f"- `data` Address: none at this point (sea or outside Japan). — 出典：国土地理院 逆ジオコーダ, {url}"], raw
    muni = res.get("muniCd", "")
    try:
        js = (get_bytes("https://maps.gsi.go.jp/js/muni.js") or b"").decode("utf-8")
        line = next(x for x in js.splitlines() if f'MUNI_ARRAY["{muni.lstrip("0")}"]' in x or f'MUNI_ARRAY["{muni}"]' in x)
        _, pref, _, city = line.split("'")[1].split(",")[:4]
        raw["muni"] = line.split("'")[1]
    except (StopIteration, ValueError, OSError):
        pref, city = "", ""
    name = f"{pref}{city} {res.get('lv01Nm', '')}".strip()
    return [f"- `data` Address: {name} (市区町村コード {muni}). — 出典：国土地理院 逆ジオコーダ, {url}"], raw


def elevation(site: Site):
    url = "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php?" + \
          urllib.parse.urlencode({"lon": site.lon, "lat": site.lat, "outtype": "JSON"})
    raw = _json(url) or {}
    h = raw.get("elevation")
    if not isinstance(h, (int, float)):
        return [f"- `data` Elevation: no value here in the GSI DEM. — 出典：国土地理院 標高API, {url}"], raw
    return [f"- `data` Elevation {h:g} m (DEM: {raw.get('hsrc', '?')}). — 出典：国土地理院 標高API, {url}"], raw


def landform(site: Site, z: int = 14):
    """The landform polygon the point is in. Polygons are cut at tile edges, so
    near an edge the neighbouring tile is asked too."""
    fx, fy = tile_xy(site.lat, site.lon, z)
    cx, cy = int(fx), int(fy)
    tiles = [(cx, cy)]
    near = lambda f: -1 if f < 0.02 else 1 if f > 0.98 else 0  # noqa: E731
    ex, ey = near(fx - cx), near(fy - cy)
    tiles += [t for t in ((cx + ex, cy), (cx, cy + ey), (cx + ex, cy + ey)) if t != (cx, cy)]
    lines, raw = [], {}
    for layer, kind in LANDFORM_LAYERS:
        for x, y in dict.fromkeys(tiles):
            url = f"{GSI}/{layer}/{z}/{x}/{y}.geojson"
            data = _json(url)
            hit = polygon_at((data or {}).get("features", []), site.lon, site.lat)
            # the tiles are large and can be fetched again: keep the polygon the point is in
            raw[url] = None if data is None else {"features": len(data.get("features", [])), "at_point": hit}
            if hit:
                code = str(hit.get("properties", {}).get("code", ""))
                group, name = LANDFORM.get(code, ("unknown class", "?"))
                label = "Landform" if kind == "natural" else "Made ground"
                lines.append(f"- `data` {label}: {group} ({name}; code {code}). "
                             f"— 出典：国土地理院 ベクトルタイル「地形分類（{'自然地形' if kind == 'natural' else '人工地形'}）」, {url}")
                break
    if not any(x.startswith("- `data` Landform") for x in lines):
        lines.insert(0, f"- `data` Landform: not mapped at this point. — 出典：国土地理院 ベクトルタイル「地形分類」, "
                        f"{GSI}/{LANDFORM_LAYERS[0][0]}/{z}/{cx}/{cy}.geojson")
    return lines, raw


def faults(site: Site):
    """The nearest active fault line, searched close first (finer), then wider."""
    src = f"— 出典：国土地理院 活断層図（都市圏活断層図）, {GSI}/afm/{{z}}/{{x}}/{{y}}.png"
    raw, seen_any = {"searched": []}, False
    for z, radius in FAULT_SEARCH:
        urls, px, py = _around(site.lat, site.lon, z, radius, lambda z, x, y: f"{GSI}/afm/{z}/{x}/{y}.png")
        mask, seen = _mosaic(urls, red_lines)
        m_px = metres_per_px(site.lat, z)
        reach = distance(radius * 256 * m_px)
        hits = nearest(mask, px, py, m_px)
        raw["searched"].append({"zoom": z, "tiles": seen, "reach_m": round(radius * 256 * m_px)})
        seen_any = seen_any or bool(seen)
        if hits:
            break
    if not seen_any:
        return [f"- `data` Active faults: no 活断層図 sheet covers this area (it maps the faults near cities only). {src}"], raw
    raw["nearest"] = [{"m": round(m), "direction": d} for m, d, _ in hits]
    if not hits:
        return [f"- `data` Active faults: no fault line on the 活断層図 within {reach}. {src}"], raw
    said = f"nearest fault line {distance(hits[0][0])} {hits[0][1]}"
    if len(hits) > 1:
        said += f"; on the other side {distance(hits[1][0])} {hits[1][1]}"
    return [f"- `data` Active faults: {said} (an estimate: red lines read by colour from the map image, searched {reach} round; the tiles carry no fault names). {src}"], raw


def _zone(site: Site, layers: list[tuple[str, str]], what: str):
    m_px = metres_per_px(site.lat, HAZARD_Z)
    reach = distance(HAZARD_R * 256 * m_px)
    inside, near, raw = [], None, {}
    for layer, name in layers:
        urls, px, py = _around(site.lat, site.lon, HAZARD_Z, HAZARD_R, lambda z, x, y, l=layer: f"{PORTAL}/{l}/{z}/{x}/{y}.png")
        mask, seen = _mosaic(urls, painted)
        hits = nearest(mask, px, py, m_px)
        here = bool(mask[int(py), int(px)])
        raw[layer] = {"tiles": seen, "inside": here, "nearest_m": round(hits[0][0]) if hits else None}
        if here:
            inside.append(name)
        elif hits and (near is None or hits[0][0] < near[0]):
            near = (hits[0][0], hits[0][1], name)
    src = f"— 出典：ハザードマップポータルサイト, {PORTAL}/{layers[0][0]}/{{z}}/{{x}}/{{y}}.png"
    if inside:
        return f"- `data` {what}: the field is INSIDE one ({', '.join(inside)}). {src}", raw
    if near:
        return f"- `data` {what}: the field is outside; nearest {distance(near[0])} {near[1]} ({near[2]}). {src}", raw
    return f"- `data` {what}: the field is outside; none within {reach}. {src}", raw


def hazards(site: Site):
    sediment, raw1 = _zone(site, SEDIMENT, "土砂災害警戒区域")
    flood, raw2 = _zone(site, [(FLOOD, "想定最大規模")], "洪水浸水想定区域")
    return [sediment, flood], {**raw1, **raw2, "zoom": HAZARD_Z}


def sheet_cell(lat: float, lon: float) -> tuple[float, float]:
    """(west longitude, north latitude) of the 1:50,000 sheet the point is on. A
    point on an edge is on the sheet east or south of it."""
    return math.floor(round(lon * 4, 9)) / 4, math.ceil(round(lat * 6, 9)) / 6


def _dms(deg: float) -> str:
    d, m = divmod(round(deg * 60), 60)
    return f"{d}°{m:02d}′"


def _catalogue(page: str) -> tuple[list[tuple[tuple[int, int, int, int], str]], dict[str, dict]]:
    """The index map's rectangles (x1, y1, x2, y2; code) and the published sheets by code."""
    rects = [(tuple(map(int, m[:4])), m[4]) for m in
             re.findall(r'<area shape="rect" coords="(\d+),(\d+),(\d+),(\d+)" href="#(\d+)"', page)]
    sheets = {}
    for row in page.split("<tr>"):
        m = re.search(r'id="(\d+)" class="group1" title="5万分の1地質図幅\s+(\d+)\s*［([^］]+)］-(\d+)\s*「([^」]+)」', row)
        if not m:
            continue
        year = re.search(r"発行年：(\d{4})", row)
        pdfs = re.findall(r"url=(/data/50KGM/PDF/[^\"]+_D[^\"/]*\.pdf)", row)
        # the corrected edition (_V2) over the plain one over the light one (-L)
        pdf = max(pdfs, key=lambda u: ("_V" in u, "-L" not in u), default=None)
        elsewhere = re.search(r'説明書\s*（<a href="([^"]+)"', row)  # Hokkaido: at 道総研
        jpg = re.search(r"url=(/data/50KGM/JPG/[^\"]+\.jpg)", row)
        sheets[m[1]] = {"region": m[2], "region_name": m[3], "no": m[4], "name": m[5].strip(),
                        "year": year[1] if year else None,
                        "report": f"https://www.gsj.jp{pdf}" if pdf else elsewhere[1] if elsewhere else None,
                        "map": f"https://www.gsj.jp{jpg[1]}" if jpg else None}
    return rects, sheets


def sheet(site: Site):
    """The 1:50,000 geological map sheet the point is on, from the 産総研 catalogue,
    and where its report is. The point's formation name ("terrace deposits") does
    not say what rock the gravels are; the report's text does."""
    west, north = sheet_cell(site.lat, site.lon)
    cell = f"{_dms(west)}–{_dms(west + 0.25)}E, {_dms(north - 1 / 6)}–{_dms(north)}N"
    raw = {"cell": [west, north], "pages": []}
    head = "- `hypothesis` Parent material: not looked up."
    for page_no, (lon0, n0, x0, y0, cols, rows) in SHEET_GRID.items():
        col, row = round((west - lon0) * 4), n0 - round(north * 6)
        if not (0 <= col < cols and 0 <= row < rows):
            continue
        url = CATALOGUE.format(page_no)
        raw["pages"].append(url)
        rects, sheets = _catalogue((get_bytes(url) or b"").decode("utf-8", "replace"))
        if not rects:  # gone, or a maintenance page: not the same as "no sheet here"
            raise RuntimeError(f"no index map on {url}")
        px, py = x0 + (col + 0.5) * SHEET_PX[0], y0 + (row + 0.5) * SHEET_PX[1]
        code = next((c for (x1, y1, x2, y2), c in rects if x1 <= px < x2 and y1 <= py < y2), None)
        if code is None:
            continue
        s = sheets.get(code)
        raw["sheet"] = {"code": code, **(s or {})}
        src = f"— 出典：産総研地質調査総合センター 地質図カタログ, {url}#{code}"
        if s is None:
            region = next(iter(sheets.values()), {})
            label = f"{int(code[:2])}［{region.get('region_name', '?')}］-{code[2:]}"
            return [f"{head} No 1:50,000 geological map is published for this sheet ({label}; {cell}), "
                    f"so there is no report to read. {src}"], raw
        label = f"{s['name']}, 5万分の1地質図幅 {s['region']}［{s['region_name']}］-{s['no']}"
        if s["report"]:
            return [f"{head} The 1:50,000 report {label} ({s['year']}) describes the rocks and deposits of this "
                    f"sheet ({cell}); read its section on the unit at this point. {src}, {s['report']}"], raw
        return [f"{head} The 1:50,000 map {label} ({s['year']}) is published without a report online; "
                f"its legend names the units ({cell}). {src}" + (f", {s['map']}" if s["map"] else "")], raw
    return [f"{head} This point ({cell}) is not on the 産総研 catalogue's 1:50,000 index maps "
            f"(the islands' pages are not read). — 出典：産総研地質調査総合センター 地質図カタログ, "
            f"https://www.gsj.jp/Map/JP/geology4.html"], raw


def soil_hint(site: Site):
    url = f"https://soil-inventory.rad.naro.go.jp/figure.html?lat={site.lat:.6f}&lng={site.lon:.6f}&zoom=15"
    return [f"- `hypothesis` Soil type: not looked up (no point API). Check the 農研機構 日本土壌インベントリー "
            f"soil map at this point and write the class here. — {url}"], {"url": url}
