"""Japanese primary data, offline: the answers recorded on 2026-10-30 for the
second farm (新居浜市萩生), replayed at lookup_jp.get_bytes. The fault map
tiles are kept as their red pixels only, except the field's own tile."""

import io
import json
import urllib.error
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from fieldnotes import cli, lookup, lookup_jp
from fieldnotes.site import Site

FIX = Path(__file__).parent / "fixtures" / "lookup_jp_niihama"
LAT, LON = 33.912408614720086, 133.26414612740723
NIIHAMA = Site(lat=LAT, lon=LON, country="JP")


@pytest.fixture
def recorded(monkeypatch):
    manifest = json.loads((FIX / "manifest.json").read_text())
    asked = []

    def get(url):
        asked.append(url)
        return (FIX / manifest[url]).read_bytes() if manifest[url] else None
    monkeypatch.setattr(lookup_jp, "get_bytes", get)
    return asked


def test_niihama_settles_the_place(recorded):
    lines = [x for fn in (lookup_jp.address, lookup_jp.elevation, lookup_jp.landform, lookup_jp.faults,
                          lookup_jp.hazards) for x in fn(NIIHAMA)[0]]
    text = "\n".join(lines)
    assert "Address: 愛媛県新居浜市 萩生 (市区町村コード 38205). — 出典：国土地理院 逆ジオコーダ" in text
    assert "Elevation 97.1 m (DEM: 1m（レーザ）)" in text
    assert "Landform: 台地・段丘 (更新世段丘; code 10314)" in text
    assert "nearest fault line 210 m S; on the other side 1.1 km N" in text  # 石鎚断層, 岡村断層
    assert "土砂災害警戒区域: the field is outside; nearest 150 m S (土石流). — 出典：ハザードマップポータルサイト" in text
    assert "洪水浸水想定区域: the field is outside; nearest 300 m SW" in text
    # the point is 0.1 % from the east edge of its z14 tile: the neighbour was asked too
    assert any("/14/14257/6549.geojson" in u for u in recorded)


def test_fault_lines_are_told_from_the_map_by_colour():
    tile = np.asarray(Image.open(FIX / "25295ea902d9.png").convert("RGBA"))  # the field's tile as served
    lines = lookup_jp.red_lines(tile)
    assert 0 < lines.sum() < 0.03 * lines.size  # thin lines, not the orange landform areas
    noise = tile.copy()
    noise[100, 100, :3] = (230, 20, 20)  # one stray red pixel is not a line
    assert lookup_jp.red_lines(noise)[100, 100] == lines[100, 100]


def _png(mask: np.ndarray) -> bytes:
    rgba = np.zeros((256, 256, 4), np.uint8)
    rgba[mask] = (255, 0, 0, 255)
    buf = io.BytesIO()
    Image.fromarray(rgba).save(buf, "PNG")
    return buf.getvalue()


def test_a_polygon_only_in_the_neighbouring_tile(monkeypatch):
    site = Site(lat=LAT, lon=LON, country="JP")
    fx, fy = lookup_jp.tile_xy(LAT, LON, 14)
    east = int(fx) + 1
    square = [[[LON - 0.001, LAT - 0.001], [LON + 0.001, LAT - 0.001], [LON + 0.001, LAT + 0.001],
               [LON - 0.001, LAT + 0.001], [LON - 0.001, LAT - 0.001]]]
    tiles = {f"experimental_landformclassification1/14/{east}/{int(fy)}":
             {"features": [{"geometry": {"type": "Polygon", "coordinates": square}, "properties": {"code": "10501"}}]}}
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: next(
        (json.dumps(v).encode() for k, v in tiles.items() if k in url), None))
    lines, _ = lookup_jp.landform(site)
    assert "Landform: 扇状地 (扇状地; code 10501)" in lines[0]


def test_inside_a_zone_is_said_plainly(monkeypatch):
    every = _png(np.ones((256, 256), bool))
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: every if "dosekiryu" in url else None)
    lines, raw = lookup_jp.hazards(NIIHAMA)
    assert "土砂災害警戒区域: the field is INSIDE one (土石流)" in lines[0]
    assert "洪水浸水想定区域: the field is outside; none within 1.0 km" in lines[1]
    assert raw["05_dosekiryukeikaikuiki"]["inside"] is True


def test_lookup_in_japan_writes_place_hazards_and_soil_hint(tmp_path, monkeypatch, recorded):
    monkeypatch.setattr(lookup, "get_json", lambda url, **kw: {"elevation": [97.0]} if "open-meteo" in url else {})
    assert cli.main(["--root", str(tmp_path), "init", "--place", "新居浜市, 愛媛県", "--country", "JP",
                     "--lat", str(LAT), "--lon", str(LON)]) == 0
    lookup.lookup(tmp_path / "records")
    text = (tmp_path / "records" / "lookup.md").read_text()
    heads = [x for x in text.splitlines() if x.startswith("## ")]
    assert heads[:2] == ["## Place", "## Terrain"] and "## Faults and hazards" in heads
    assert text.index("Elevation 97.1 m (DEM") < text.index("Elevation 97 m. — Open-Meteo")
    assert "`hypothesis` Soil type: not looked up (no point API). Check the 農研機構 日本土壌インベントリー" in text
    raw = json.loads((tmp_path / "records" / "lookup" / "faults_jp.json").read_text())
    assert raw["nearest"][0] == {"m": 211, "direction": "S"}


def test_a_gsi_server_that_is_down_is_named(tmp_path, monkeypatch):
    def down(url):
        raise urllib.error.URLError("timed out")
    monkeypatch.setattr(lookup_jp, "get_bytes", down)
    monkeypatch.setattr(lookup, "get_json", lambda url, **kw: {"elevation": [97.0]} if "open-meteo" in url else {})
    cli.main(["--root", str(tmp_path), "init", "--place", "x", "--country", "JP", "--lat", str(LAT), "--lon", str(LON)])
    lookup.lookup(tmp_path / "records")
    text = (tmp_path / "records" / "lookup.md").read_text()
    assert "(国土地理院 活断層図: not reached on" in text and "(ハザードマップポータルサイト: not reached on" in text
    assert "Elevation 97 m. — Open-Meteo" in text


def test_outside_japan_none_of_this_is_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: pytest.fail(f"asked {url}"))
    monkeypatch.setattr(lookup, "get_json", lambda url, **kw: {"elevation": [5.0]} if "open-meteo" in url else {})
    cli.main(["--root", str(tmp_path), "init", "--place", "Nakuru", "--country", "KE", "--lat", "-0.3", "--lon", "36.07"])
    lookup.lookup(tmp_path / "records")
    assert "国土地理院" not in (tmp_path / "records" / "lookup.md").read_text()


def test_no_fault_close_by_looks_wider(monkeypatch):
    """Nothing within 2 km at z15: the z14 tiles (4 km) are asked, and a line
    in a corner beyond the covered circle does not count."""
    blank = np.full((256, 256, 3), 255, np.uint8)
    line = blank.copy()
    line[40:43, :] = (220, 20, 20)  # a fault line across the tile north of the point's tile
    png = lambda a: (lambda b: (Image.fromarray(a).save(b, "PNG"), b.getvalue())[1])(io.BytesIO())  # noqa: E731
    fx, fy = lookup_jp.tile_xy(LAT, LON, 14)
    north = f"/afm/14/{int(fx)}/{int(fy) - 1}.png"
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: png(line) if url.endswith(north) else png(blank))
    lines, raw = lookup_jp.faults(NIIHAMA)
    assert [s["zoom"] for s in raw["searched"]] == [15, 14]
    assert "nearest fault line" in lines[0] and "3.1 km N (searched 4.1 km round" in lines[0]
