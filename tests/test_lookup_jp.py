"""Japanese primary data, offline: the answers recorded on 2026-10-30 for the
second farm (新居浜市萩生), replayed at lookup_jp.get_bytes. The fault map
tiles are kept as their red pixels only, except the field's own tile."""

import io
import json
import math
import urllib.error
from datetime import date
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


def test_lookup_in_japan_writes_place_hazards_and_soil(tmp_path, monkeypatch, recorded):
    monkeypatch.setattr(lookup, "get_json", lambda url, **kw: {"elevation": [97.0]} if "open-meteo" in url else {})
    assert cli.main(["--root", str(tmp_path), "init", "--place", "新居浜市, 愛媛県", "--country", "JP",
                     "--lat", str(LAT), "--lon", str(LON)]) == 0
    lookup.lookup(tmp_path / "records")
    text = (tmp_path / "records" / "lookup.md").read_text()
    heads = [x for x in text.splitlines() if x.startswith("## ")]
    assert heads[:3] == ["## Place", "## Parcel", "## Terrain"] and "## Faults and hazards" in heads
    assert "the field point lies in no parcel" in text
    assert text.index("Elevation 97.1 m (DEM") < text.index("Elevation 97 m. — Open-Meteo")
    assert "`data` Soil type: 礫質水田化疑似グライ土 (H2c1p2)." in text and "出典：農研機構、日本土壌インベントリー (CC BY 4.0)" in text
    geology = text[text.index("## Geology"):text.index("## Faults and hazards")]
    assert "The 1:50,000 report 新居浜" in geology
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
    assert "(筆ポリゴン: not reached on" in text
    assert "Elevation 97 m. — Open-Meteo" in text


def test_outside_japan_none_of_this_is_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: pytest.fail(f"asked {url}"))
    monkeypatch.setattr(lookup, "get_json", lambda url, **kw: {"elevation": [5.0]} if "open-meteo" in url else {})
    cli.main(["--root", str(tmp_path), "init", "--place", "Nakuru", "--country", "KE", "--lat", "-0.3", "--lon", "36.07"])
    lookup.lookup(tmp_path / "records")
    assert "国土地理院" not in (tmp_path / "records" / "lookup.md").read_text()


ISHII = Site(lat=34.0801, lon=134.4454, country="JP")


def test_the_map_sheet_is_found_from_the_point(recorded):
    assert lookup_jp.sheet_cell(LAT, LON) == (133.25, 34.0)
    assert lookup_jp.sheet_cell(ISHII.lat, ISHII.lon) == (134.25, 34 + 1 / 6)
    lines, raw = lookup_jp.sheet(NIIHAMA)
    assert lines[0].startswith("- `hypothesis` Parent material: not looked up. The 1:50,000 report 新居浜, "
                               "5万分の1地質図幅 13［高知］-040 (2013) describes the rocks and deposits of this sheet "
                               "(133°15′–133°30′E, 33°50′–34°00′N)")
    assert lines[0].endswith("geology4-13.html#13040, https://www.gsj.jp/data/50KGM/PDF/GSJ_MAP_G050_13040_2013_D.pdf")
    assert raw["sheet"]["code"] == "13040" and raw["pages"] == ["https://www.gsj.jp/Map/JP/geology4-13.html"]
    lines, raw = lookup_jp.sheet(ISHII)  # 徳島: no 1:50,000 map yet
    assert "No 1:50,000 geological map is published for this sheet (13［高知］-033; 134°15′–134°30′E, 34°00′–34°10′N)" in lines[0]


def test_a_point_on_a_sheet_corner_is_on_the_sheet_south_east_of_it(recorded):
    corner = Site(lat=34.0, lon=133.25, country="JP")  # the north-west corner of 新居浜
    assert lookup_jp.sheet_cell(corner.lat, corner.lon) == (133.25, 34.0)
    assert lookup_jp.sheet(corner)[1]["sheet"]["code"] == "13040"
    across = Site(lat=34.0001, lon=133.2499, country="JP")  # just over the corner: the sheet north-west of it
    assert lookup_jp.sheet_cell(across.lat, across.lon) == (133.0, 34 + 1 / 6)
    assert lookup_jp.sheet(across)[1]["sheet"]["code"] == "13028"
    assert lookup_jp.sheet_cell(33 + 5 / 6, 133.5) == (133.5, 33 + 5 / 6)  # 10′ steps do not drift


def test_a_catalogue_page_without_its_index_map_is_not_reached(monkeypatch):
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: "<p>メンテナンス中</p>".encode())
    with pytest.raises(RuntimeError, match="no index map"):
        lookup_jp.sheet(NIIHAMA)
    assert "not on the 産総研 catalogue" in lookup_jp.sheet(Site(lat=26.21, lon=127.68, country="JP"))[0][0]  # 那覇


def test_the_parcel_the_field_lies_in(recorded):
    lines, raw = lookup_jp.parcel(Site(lat=34.0801, lon=134.4454, country="JP"))  # the home field, Ishii
    used = date.today()
    assert lines[0].startswith("- `data` Parcel (筆ポリゴン): the field point lies in a parcel of 602 m², read as 田 in 2020 "
                               "(id afafc863-45b4-40b3-866a-21e3c55b1ed5); within 100 m, 24 other parcels (24 田).")
    assert "they show neither 筆界 nor rights" in lines[0]
    assert f"出典：「筆ポリゴンデータ（2026年度公開）」（農林水産省）（{used.year}年{used.month}月{used.day}日に利用）を加工して作成" in lines[0]
    assert lines[1].startswith("- `reference` 全国農地ナビ") and lines[1].endswith("https://map.maff.go.jp/")
    assert raw["parcel"]["geometry"]["type"] == "Polygon" and raw["area_m2"] == 601.7
    lines, raw = lookup_jp.parcel(NIIHAMA)  # beside a house: no parcel
    assert "the field point lies in no parcel (land outside the 面積調査, such as a garden); within 100 m, 40 parcels (36 田, 4 畑)" in lines[0]
    assert raw["parcel"] is None


def test_parcel_area_on_the_ground(recorded):
    k = math.pi / 180 * lookup_jp.EARTH_R
    square = [[134.0, 34.0], [134.001, 34.0], [134.001, 34.001], [134.0, 34.001], [134.0, 34.0]]
    assert lookup_jp.ring_area_m2(square) == pytest.approx((0.001 * k) ** 2 * math.cos(math.radians(34.0005)), rel=1e-6)
    hole = [[134.0004, 34.0004], [134.0006, 34.0004], [134.0006, 34.0006], [134.0004, 34.0006], [134.0004, 34.0004]]
    with_hole = lookup_jp.polygon_area_m2({"type": "Polygon", "coordinates": [square, hole]})
    assert with_hole == pytest.approx(lookup_jp.ring_area_m2(square) * (1 - 0.04), rel=1e-4)
    # the service's own area is in Web-Mercator m²: cos² of the latitude brings it to the ground
    _, raw = lookup_jp.parcel(Site(lat=34.0801, lon=134.4454, country="JP"))
    mercator = raw["parcel"]["properties"]["SHAPE__Area"]
    assert raw["area_m2"] == pytest.approx(mercator * math.cos(math.radians(34.0801)) ** 2, rel=0.01)


def test_the_soil_class_is_read_from_the_map_colour(recorded):
    lines, raw = lookup_jp.soil(Site(lat=34.0801, lon=134.4454, country="JP"))  # the home field, Ishii
    assert lines[0].startswith("- `data` Soil type: 細粒質水田化褐色低地土 (F4c1t1). 次表層の土性が重埴土")
    assert "誤差を含む" in lines[0] and lines[0].endswith("tile/figure/15/28621/13080.png")
    assert raw["rgba"] == [4, 136, 168, 255]
    lines, raw = lookup_jp.soil(NIIHAMA)  # on the last pixel column of its tile
    assert "礫質水田化疑似グライ土 (H2c1p2). 土壌表面から60cm以内に礫層が現れる" in lines[0]


def test_a_colour_not_in_the_legend_is_not_guessed(monkeypatch):
    legend = "var figureRGB =[\n\t[4,136,168,\"F4c1t1\",\"細粒質水田化褐色低地土\",\"...\"],\n];".encode()
    def tile(rgba):
        buf = io.BytesIO()
        Image.fromarray(np.full((256, 256, 4), rgba, np.uint8)).save(buf, "PNG")
        return buf.getvalue()
    near = tile((4, 136, 169, 255))  # one unit off: the site would take the nearest; here it is not guessed
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: legend if url.endswith(".js") else near)
    line = lookup_jp.soil(NIIHAMA)[0][0]
    assert "RGB (4, 136, 169), is not in its legend; not guessed" in line and "F4c1t1" not in line
    clear = tile((0, 0, 0, 0))
    monkeypatch.setattr(lookup_jp, "get_bytes", lambda url: legend if url.endswith(".js") else clear)
    assert "not mapped at this point" in lookup_jp.soil(NIIHAMA)[0][0]


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
    assert "nearest fault line" in lines[0] and "3.1 km N (an estimate: red lines read by colour from the map image, searched 4.1 km round" in lines[0]
