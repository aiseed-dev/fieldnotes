"""What the phone app's 読む / 名詞 views show (appdata.py); no Flet, no network."""

import os
import time
from pathlib import Path

from PIL import Image

from fieldnotes import appdata


def jpg(path: Path, size=(40, 30)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (10, 120, 30)).save(path, "JPEG")
    return path


def test_photo_days_newest_first_and_only_with_photos(tmp_path):
    jpg(tmp_path / "north" / "2026-10-21" / "100000-a.jpg")
    jpg(tmp_path / "north" / "2026-10-28" / "100000-b.JPG")
    (tmp_path / "north" / "2026-10-25").mkdir()  # empty day
    (tmp_path / "north" / "notes").mkdir()
    assert appdata.photo_days(tmp_path, "north") == ["2026-10-28", "2026-10-21"]
    assert appdata.photo_days(tmp_path, "nowhere") == []


def test_photo_fields_skips_fields_without_photos(tmp_path):
    jpg(tmp_path / "north" / "2026-10-21" / "100000-a.jpg")
    (tmp_path / "empty" / "2026-10-21").mkdir(parents=True)
    (tmp_path / "Bad Name" / "2026-10-21").mkdir(parents=True)
    assert appdata.photo_fields(tmp_path) == ["north"]


def test_day_photos_sorted_by_time(tmp_path):
    for n in ("110000-b.jpg", "090000-a.jpg", "100000-c.jpeg"):
        jpg(tmp_path / "f" / "2026-10-28" / n)
    (tmp_path / "f" / "2026-10-28" / "voice.wav").write_bytes(b"")
    assert [p.name for p in appdata.day_photos(tmp_path, "f", "2026-10-28")] == ["090000-a.jpg", "100000-c.jpeg", "110000-b.jpg"]


def test_overlay_paths_numeric_order_and_same_day_only(tmp_path):
    rec = tmp_path / "f"
    for n in (1, 2, 10):
        jpg(rec / f"2026-10-28-overlay-{n}.jpg")
    jpg(rec / "2026-10-21-overlay-1.jpg")
    (rec / "2026-10-28.md").write_text("x")
    assert [p.name for p in appdata.overlay_paths(tmp_path, "f", "2026-10-28")] == [
        "2026-10-28-overlay-1.jpg", "2026-10-28-overlay-2.jpg", "2026-10-28-overlay-10.jpg"]


def test_concept_fields(tmp_path):
    (tmp_path / "_concepts").mkdir()
    (tmp_path / "_concepts" / "north.md").write_text("x")
    assert appdata.concept_fields(tmp_path) == ["north"]
    assert appdata.concept_fields(tmp_path / "none") == []


def test_split_conf():
    assert appdata.split_conf("Lush and even. [0.8]") == ("Lush and even.", "0.8")
    assert appdata.split_conf("no confidence here") == ("no confidence here", None)
    assert appdata.split_conf("pH ~5.5-6.5; up [0.45]") == ("pH ~5.5-6.5; up", "0.45")


def test_labels():
    assert appdata.key_label("dominant") == "優勢な草"
    assert appdata.key_label("unknown_key") == "unknown_key"
    assert appdata.last_label("-") == "まだ使っていない"
    assert appdata.last_label("2026-10-28 no match") == "2026-10-28 見つからず"
    assert appdata.last_label("2026-10-28 23.4%, 12 objects") == "2026-10-28 23.4%, 12 個"


def test_shrunk_jpeg_limits_side_and_follows_exif_orientation(tmp_path):
    p = tmp_path / "big.jpg"
    im = Image.new("RGB", (400, 200), "green")
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° on display: upright photo is 200 wide, 400 tall
    im.save(p, "JPEG", exif=exif)
    import io
    out = Image.open(io.BytesIO(appdata.shrunk_jpeg(p, 100)))
    assert out.size == (50, 100)


def test_shrunk_jpeg_cache_follows_file_changes(tmp_path):
    import io
    p = tmp_path / "a.jpg"
    Image.new("RGB", (100, 100), "red").save(p, "JPEG")
    first = appdata.shrunk_jpeg(p, 50)
    Image.new("RGB", (100, 100), "blue").save(p, "JPEG")
    os.utime(p, (time.time() + 5, time.time() + 5))
    assert appdata.shrunk_jpeg(p, 50) != first
    assert Image.open(io.BytesIO(appdata.shrunk_jpeg(p, 50))).size == (50, 50)


# ---- marking (WP18 item 1) -------------------------------------------------

def _record():
    from fieldnotes.records import Observation, Record
    return Record(field="uncut", date="2026-11-02", ai_model="muse-spark-1.3", observations=[
        Observation("overall", "Dense stand. [0.8]", "right"),
        Observation("zone", "SE corner: cut strip [0.7]"),
        Observation("zone", "N edge: ogi [0.6]", "wrong", "that is the neighbour's"),
    ], voice=[Observation("work", "cut the path")], checks=[Observation("h3", "agrees: no mud [0.8]")])


def test_line_refs_number_repeated_keys_the_way_mark_does():
    refs = appdata.line_refs(_record())
    assert [(r.group, r.ref) for r in refs] == [
        ("ai", "overall"), ("ai", "zone"), ("ai", "zone#2"), ("voice", "work"), ("checks", "h3")]


def test_mark_count_covers_every_model_line_of_the_day():
    rec = _record()
    assert appdata.mark_count(rec) == (1, 1, 5)
    assert appdata.count_label(rec) == "今日の印: ✓ 1、✗ 1（AI の 5 行のうち）"
    from fieldnotes.ui import Words
    assert appdata.count_label(rec, Words("en")) == "Marked today: 1 ✓, 1 ✗ of 5 AI lines"


# ---- readings, not answers (WP18 item 2) ---------------------------------

def _farm(root: Path, name: str, text: str):
    rec = root / name / "records" / "uncut"
    rec.mkdir(parents=True)
    (rec / "2026-10-28.md").write_text(text, encoding="utf-8")
    return root / name


def test_readings_stand_side_by_side_by_key(tmp_path, monkeypatch):
    ja = _farm(tmp_path, "farm", "---\nfield: uncut\ndate: '2026-10-28'\nphotos: [a.jpg]\nweather: {tmax: 18}\n"
               "coverage: {leaf: 3.0}\n---\n\n## AI observation (muse-spark-1.3)\n- overall: 密生 [0.8]\n- zone: 南 [0.7]\n"
               "- zone: 北 [0.6]\n\n## Earlier AI lines\n- overall: 前の読み [0.5]  → farmer: wrong (no)\n\n## Farmer note (none, ja)\n(none)\n")
    _farm(tmp_path, "farm-en", "---\nfield: uncut\ndate: '2026-10-28'\nphotos: [a.jpg]\n---\n\n## AI observation (muse-spark-1.3)\n"
          "- overall: Dense [0.8]\n- zone: S [0.7]\n- dominant: ogi [0.9]\n\n## Farmer note (none, en)\n(none)\n")
    _farm(tmp_path, "other", "---\nfield: uncut\ndate: '2026-10-28'\n---\n\n## AI observation (x)\n- overall: elsewhere\n\n## Farmer note (none, en)\n(none)\n")
    monkeypatch.delenv(appdata.ALSO, raising=False)
    assert [p.name for p in appdata.sibling_roots(ja)] == ["farm-en"]
    monkeypatch.setenv(appdata.ALSO, str(tmp_path / "other"))
    assert [p.name for p in appdata.sibling_roots(ja)] == ["farm-en", "other"]
    monkeypatch.delenv(appdata.ALSO)

    found = appdata.readings(ja, "uncut", "2026-10-28")
    assert [(r.label, r.root is not None, len(r.refs)) for r in found] == [("farm", True, 3), ("earlier", False, 1), ("farm-en", True, 3)]
    rows = appdata.side_by_side(found)
    assert [(g, ref, [c.line.text.split()[0] if c else None for c in cells]) for g, ref, cells in rows] == [
        ("ai", "overall", ["密生", "前の読み", "Dense"]),
        ("ai", "zone", ["南", None, "S"]),
        ("ai", "zone#2", ["北", None, None]),
        ("ai", "dominant", [None, None, "ogi"]),
    ]
    assert appdata.readings(tmp_path / "nowhere", "uncut", "2026-10-28") == []
    # one reading: its lines in file order, no pairing
    assert [ref for _, ref, _ in appdata.side_by_side(found[2:])] == ["overall", "zone", "dominant"]


def test_sources_say_what_the_model_was_given(tmp_path):
    from fieldnotes.records import Observation, Record
    from fieldnotes.ui import Words
    rec = Record(field="uncut", date="2026-10-28", photos=["a", "b"], weather={"tmax": 18.0}, coverage={"leaf": 1.0, "bare soil": 2.0})
    assert appdata.sources(rec, tmp_path, Words("en")) == "Given: 2 photo(s), SAM cover (2 nouns), weather (Open-Meteo)"
    (tmp_path / "site.md").write_text("---\nplace: x\n---\n")
    Record(field="uncut", date="2026-10-21", observations=[Observation("overall", "x", "wrong", "y")]).save(tmp_path)
    assert appdata.sources(rec, tmp_path, Words("en")) == (
        "Given: 2 photo(s), SAM cover (2 nouns), weather (Open-Meteo), site.md, 1 earlier day(s) (1 ✗)")
    assert appdata.model_of(rec, "ai") == "none"


# ---- the walk (WP18 item 3) ----------------------------------------------

def test_walk_map_draws_the_points_on_the_parcel_true_to_scale(tmp_path):
    from test_walk import E, N, PARCEL, S, W, parcel
    import json
    root = tmp_path
    parcel(root)
    d = 0.000001  # just inside the corners (a point on the edge counts as outside)
    found = [{"file": "a.jpg", "lat": N - d, "lon": W + d}, {"file": "b.jpg", "lat": (S + N) / 2, "lon": (W + E) / 2},
             {"file": "c.jpg", "lat": None, "lon": None}, {"file": "d.jpg", "lat": S + d, "lon": E - d}]
    m = appdata.walk_map(found, root / "records", 200, 100, pad=10)
    assert m.kind == "parcel" and m.n_gps == 3 and len(m.rings) == 1
    xs = [x for x, _ in m.rings[0]]
    ys = [y for _, y in m.rings[0]]
    # the parcel keeps its shape in metres (about 37 m x 33 m), limited by the 80 px of height
    import math
    ratio = (E - W) * math.cos(math.radians((S + N) / 2)) / (N - S)
    assert max(ys) - min(ys) == 80 and abs((max(xs) - min(xs)) - 80 * ratio) < 0.5
    near = lambda p, q: abs(p[0] - q[0]) < 1 and abs(p[1] - q[1]) < 1  # noqa: E731
    assert near(m.points[0], (min(xs), min(ys)))  # NW corner is top left
    assert m.points[2] is None
    assert near(m.points[3], (max(xs), max(ys)))  # SE corner is bottom right
    assert near(m.points[1], ((min(xs) + max(xs)) / 2, 50.0))
    # no GPS at all: nothing to draw, said so
    assert appdata.walk_map([{"file": "x.jpg"}], root / "records", 200, 100) == appdata.WalkMap("none", [], [None], 0)
    # points outside the parcel: the walk's extent, widened to show the parcel
    far = [{"file": "a.jpg", "lat": S - 0.001, "lon": W}, {"file": "b.jpg", "lat": S - 0.0012, "lon": E}]
    m = appdata.walk_map(far, root / "records", 200, 100)
    assert m.kind == "walk" and len(m.rings) == 1 and all(p for p in m.points)
    assert max(y for _, y in m.rings[0]) < min(y for p in m.points for y in [p[1]])  # the parcel is north of the walk


def test_strip_pairs_photos_with_overlays_and_labels(tmp_path):
    from test_walk import walk_photos
    root = tmp_path
    (root / "records").mkdir()
    walk_photos(root)
    jpg(root / "records" / "uncut" / "2026-10-28-overlay-1.jpg")
    items = appdata.strip(root, "uncut", "2026-10-28")
    assert [i.n for i in items] == [1, 2, 3]
    assert [i.photo.name for i in items] == ["100000-a.jpg", "101000-b.jpg", "102000-c.jpg"]
    assert items[0].overlay.name == "2026-10-28-overlay-1.jpg" and items[1].overlay is None
    assert items[0].label.startswith("1 of 3, 10:00, NW corner")
    assert appdata.strip(root, "uncut", "2026-10-29") == []


# ---- the land and the baseline (WP18 item 4) ------------------------------

SITE = """---
place: Ishii, Tokushima, Japan
country: JP
---
# The land

- `data` — public data with its source.
- `hypothesis` — a reading, not yet checked.

## Terrain and water

- `data` 4 m above the channel to the N. — GSI DEM 1 m, https://maps.gsi.go.jp/xyz/dem/{z}/{x}/{y}.txt and https://example.org/dem.
- `record` The N side is dry (farmer, 2026-11-01).
- `hypothesis` Ground water is not near the surface here [0.6]. — Opus (Claude), 2026-11-01. Check (by growing): see below.
- `hypothesis` A plough pan at 15–20 cm [0.7]. — Opus (Claude), 2026-11-01. Check: daikon roots that fork.
- not reached on 2026-11-02

## What the farmer knows works here

"""


def land_farm(root: Path) -> Path:
    from fieldnotes.records import Observation, Record, notes_to_markdown
    rec = root / "records"
    rec.mkdir(parents=True, exist_ok=True)
    (rec / "site.md").write_text(SITE, encoding="utf-8")
    hyps = {"h1": "Ground water is not near the surface here [0.6]. — Opus (Claude), 2026-11-01. Check (by growing): see below.",
            "h2": "A plough pan at 15–20 cm [0.7]. — Opus (Claude), 2026-11-01. Check: daikon roots that fork."}
    p = rec / "_checks" / "north" / "expect.md"
    p.parent.mkdir(parents=True)
    p.write_text(notes_to_markdown({"field": "north", "kind": "expect", "model": "m", "hypotheses": hyps}, "Expectations (m)",
                                   [Observation("h1", "holds: dry soil; fails: wet soil; visible: yes"),
                                    Observation("h2", "holds: forked roots; fails: straight; visible: no")]), encoding="utf-8")
    for day, verdict in (("2026-11-01", "right"), ("2026-11-02", None)):
        Record(field="north", date=day, photos=["a"], ai_model="m", observations=[Observation("overall", "x")],
               checks=[Observation("h1", "agrees: the soil looks dry [0.6]", verdict)], checks_model="m").save(rec)
    return rec


def test_land_page_keeps_status_text_source_and_check(tmp_path):
    rec = land_farm(tmp_path)
    page = appdata.land_page(rec, "site.md")
    assert page.front["country"] == "JP"
    assert [s.heading for s in page.sections] == ["Terrain and water", "What the farmer knows works here"]
    data, record, h1, h2, bare = page.sections[0].lines
    assert (data.status, data.text) == ("data", "4 m above the channel to the N.")
    assert data.source.startswith("GSI DEM 1 m")
    assert (record.status, record.source) == ("record", "")  # the farmer's words stand as written
    assert (h1.status, h1.source, h1.check) == ("hypothesis", "Opus (Claude), 2026-11-01.", "see below.")
    assert h2.check == "daikon roots that fork."
    assert (bare.status, bare.text) == ("", "not reached on 2026-11-02")
    assert page.sections[1].lines == []  # an empty section is kept, so the screen can say so
    assert appdata.land_page(rec, "lookup.md") is None
    assert appdata.status_counts([page]) == {"data": 1, "record": 1, "hypothesis": 2}


def test_link_parts_skip_tile_templates():
    parts = appdata.link_parts("DEM, https://x/{z}/{x}/{y}.txt and https://example.org/dem.")
    assert ("https://example.org/dem.", "https://example.org/dem.") not in parts
    assert [u for _, u in parts if u] == ["https://example.org/dem"]
    assert "".join(t for t, _ in parts) == "DEM, https://x/{z}/{x}/{y}.txt and https://example.org/dem."


def test_hypothesis_checks_by_day_joined_by_words(tmp_path):
    rec = land_farm(tmp_path)
    found = appdata.hypothesis_checks(rec)
    lines = appdata.land_page(rec, "site.md").sections[0].lines
    (c1,), (c2,) = appdata.checks_of(found, lines[2]), appdata.checks_of(found, lines[3])
    assert (c1.field, c1.id, c1.visible) == ("north", "h1", True)
    assert [d for d, _ in c1.by_day] == ["2026-11-01", "2026-11-02"]
    assert (c2.id, c2.visible, c2.by_day) == ("h2", False, [])  # no photo can show a plough pan
    assert appdata.checks_of(found, lines[0]) == []  # a data line has no checks
    from fieldnotes.ui import Words
    assert [appdata.answer_label(o, Words("en")) for _, o in c1.by_day] == ["agrees ✓", "agrees"]
    assert appdata.answer_label(c1.by_day[0][1], Words("ja")) == "合う ✓"
    assert appdata.check_fields(rec) == ["north"]
    assert appdata.check_fields(tmp_path / "none") == []
    assert appdata.short_day("2026-11-02") == "11-02"


def test_hypothesis_checks_without_expectations(tmp_path):
    (tmp_path / "records").mkdir()
    assert appdata.hypothesis_checks(tmp_path / "records") == {}


def test_reader_line_names_the_reader_without_a_key(tmp_path, monkeypatch):
    """Who reads is said by name from the settings alone; no key is read to say it."""
    from fieldnotes import llm
    from fieldnotes.ui import Words
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    w = Words("en")
    assert appdata.reader_line(w, "ja") == "Next reading by muse-spark-1.3 (Muse Spark (api.meta.ai)), written in 日本語 (this device's language)"
    llm.set_training_consent(True)
    llm.set_language("en")
    assert appdata.reader_line(w, "ja") == "Next reading by muse-spark-1.3-contributor (Muse Spark (api.meta.ai)), written in English"
    llm.set_reader("glimmer", "http://10.0.0.5:11434/v1", "muse-glimmer-30B")
    assert llm.reader_name() == llm.Backend.glimmer().name == "muse-glimmer-30B@10.0.0.5"
    assert "muse-glimmer-30B@10.0.0.5 (Muse Glimmer (a machine in the house))" in appdata.reader_line(w)
