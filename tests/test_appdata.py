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
