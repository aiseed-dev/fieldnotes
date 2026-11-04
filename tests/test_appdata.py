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
