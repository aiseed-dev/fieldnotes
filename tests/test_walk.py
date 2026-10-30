"""WP13: one walk over a field read as one field (inbox GPS, walk.py, describe, timeline)."""

from __future__ import annotations

import json
from datetime import date

from conftest import DAY, FIELD, add_photos
from PIL import Image

from fieldnotes import describe, inbox, pipeline, timeline, walk
from fieldnotes.records import Record

# a 40 m x 30 m parcel; the photo points below fall in its corners and middle
W, S, E, N = 134.4450, 34.0800, 134.4454, 34.0803
PARCEL = {"type": "Feature", "geometry": {"type": "Polygon",
                                          "coordinates": [[[W, S], [E, S], [E, N], [W, N], [W, S]]]}}


def dms(v: float) -> tuple[float, float, float]:
    d = int(v)
    m = int((v - d) * 60)
    return float(d), float(m), round((v - d - m / 60) * 3600, 4)


def shot(path, when: str | None = None, lat: float | None = None, lon: float | None = None,
         facing: float | None = None, colour=(60, 120, 60)) -> None:
    """A small JPEG with the EXIF a phone writes: capture time and, if given, GPS."""
    ex = Image.Exif()
    if when:
        ex.get_ifd(inbox.EXIF_IFD)[inbox.DATETIME_ORIGINAL] = when
    if lat is not None:
        gps = ex.get_ifd(inbox.GPS_IFD)
        gps.update({1: "N" if lat >= 0 else "S", 2: dms(abs(lat)), 3: "E" if lon >= 0 else "W", 4: dms(abs(lon))})
        if facing is not None:
            gps.update({16: "T", 17: facing})
    Image.new("RGB", (64, 48), colour).save(path, "JPEG", exif=ex.tobytes())


def walk_photos(root, day=DAY, field=FIELD):
    """Three photos filed through the inbox, out of order: NW corner, middle, S edge."""
    up = root / "upload"
    up.mkdir(exist_ok=True)
    d = day.strftime("%Y:%m:%d")
    shot(up / "c.jpg", f"{d} 10:20:00", S + 0.00002, (W + E) / 2, 180.0)
    shot(up / "a.jpg", f"{d} 10:00:00", N - 0.00002, W + 0.00002, 271.5)
    shot(up / "b.jpg", f"{d} 10:10:00", (S + N) / 2, (W + E) / 2)
    for name in ("c", "a", "b"):
        inbox.file_photo(up / f"{name}.jpg", field, day, root / "photos")


def parcel(root):
    (root / "records" / "lookup").mkdir(parents=True, exist_ok=True)
    (root / "records" / "lookup" / "parcel_jp.json").write_text(
        json.dumps({"parcel": PARCEL, "near": {"type": "FeatureCollection", "features": []}}), encoding="utf-8")


def test_gps_and_time_go_into_the_index(root):
    walk_photos(root)
    up = root / "upload"
    shot(up / "nogps.jpg", "2026:10:28 10:30:00")
    inbox.file_photo(up / "nogps.jpg", FIELD, DAY, root / "photos")

    got = json.loads((root / "photos" / FIELD / "2026-10-28" / "index.json").read_text(encoding="utf-8"))
    assert [e["file"] for e in got] == ["100000-a.jpg", "101000-b.jpg", "102000-c.jpg", "103000-nogps.jpg"]
    a = got[0]
    assert a["time"] == "10:00:00" and a["facing"] == 271.5
    assert abs(a["lat"] - (N - 0.00002)) < 1e-6 and abs(a["lon"] - (W + 0.00002)) < 1e-6
    assert got[1]["facing"] is None
    assert got[3] == {"file": "103000-nogps.jpg", "time": "10:30:00", "lat": None, "lon": None, "facing": None}


def test_photos_copied_in_by_hand_are_indexed(root):
    add_photos(root)  # no EXIF at all: walk order by file name
    assert [e["file"] for e in walk.entries(root, FIELD, "2026-10-28")] == ["080000-a.jpg", "081500-b.jpg"]
    assert pipeline.photos_for(FIELD, DAY, root)[0].endswith("080000-a.jpg")


def test_positions_in_the_parcel_else_the_walk_else_none(root):
    walk_photos(root)
    found = walk.entries(root, FIELD, "2026-10-28")
    parcel(root)
    labels = walk.labels(found, root / "records")
    assert labels == {"100000-a.jpg": "1 of 3, 10:00, NW corner, facing W",
                      "101000-b.jpg": "2 of 3, 10:10, middle",
                      "102000-c.jpg": "3 of 3, 10:20, S edge, facing S"}
    assert "farm parcel" in walk.frame_note(found, root / "records")

    (root / "records" / "lookup" / "parcel_jp.json").unlink()  # no parcel: the walk's own extent
    # the walk reached only the parcel's west half, so the middle photo is at the walk's east end
    assert walk.labels(found, root / "records")["101000-b.jpg"] == "2 of 3, 10:10, E edge"
    assert "the area the walk covered" in walk.frame_note(found, root / "records")

    bare = [{**e, "lat": None, "lon": None, "facing": None} for e in found]
    assert walk.labels(bare, root / "records")["100000-a.jpg"] == "1 of 3, 10:00"
    assert "no location" in walk.frame_note(bare, root / "records")


def test_sample_spreads_along_the_walk():
    assert walk.sample(list(range(10)), 3) == [0, 4, 9]
    assert walk.sample([1, 2], 5) == [1, 2] and walk.sample([1, 2, 3], 0) == []


def _texts(messages) -> list[str]:
    return [p["text"] for p in messages[1]["content"] if p["type"] == "text"]


def _images(messages) -> int:
    return sum(p["type"] == "image_url" for p in messages[1]["content"])


def test_the_walk_is_read_in_one_request_with_numbers_and_positions(root, model, sam, wx, backend):
    walk_photos(root)
    parcel(root)
    rec = pipeline.run_observation(FIELD, DAY, root, backend)

    assert [p.rsplit("/", 1)[1] for p in rec.photos] == ["100000-a.jpg", "101000-b.jpg", "102000-c.jpg"]
    assert model.calls.count("describe") == 1 and "summary" not in model.calls
    texts = _texts(model.messages["describe"][0])
    assert "photo 1 of 3, 10:00, NW corner, facing W (100000-a.jpg)" in texts
    assert "photo 3 of 3, 10:20, S edge, facing S (102000-c.jpg)" in texts
    assert any("relative to the farm parcel" in t for t in texts)
    # SAM per photo: the spread in the record, each photo's cover in the index
    assert rec.cover_range["goldenrod"] == [50.0, 50.0]
    got = walk.entries(root, FIELD, "2026-10-28")
    assert got[0]["cover"]["goldenrod"] == 50.0 and got[0]["cover"]["bare soil"] == 25.0
    assert "goldenrod 50.0% (50.0-50.0)" in describe.day_summary(rec)


def test_a_walk_over_the_limit_is_read_in_parts_then_summed_up(root, model, sam, wx, backend):
    add_photos(root, names=[f"08{i:04d}-p" for i in range(55)], size=(16, 12))
    add_photos(root, day=date(2026, 10, 27), names=[f"08{i:04d}-q" for i in range(40)], size=(16, 12))
    pipeline.run_observation(FIELD, date(2026, 10, 27), root, backend)
    model.calls.clear()
    model.messages.clear()

    rec = pipeline.run_observation(FIELD, DAY, root, backend)

    assert model.calls.count("describe") == 2 and model.calls.count("summary") == 1
    first, second = model.messages["describe"]
    assert all(_images(m) <= walk.MAX_IMAGES for m in (first, second))
    assert any("photos 1-28 of today's 55" in t for t in _texts(first))
    assert any("photos 29-55 of today's 55" in t for t in _texts(second))
    # the earlier day shares what room is left, spread along its walk, with its reading as text
    assert any("22 of its 40 photos shown" in t for t in _texts(first))
    summary = _texts(model.messages["summary"][0])
    assert _images(model.messages["summary"][0]) == 0
    assert any(t.startswith("Reading of photos 29-55:") for t in summary)
    assert rec.ai_model == "fake-model, 55 photos read in 2 parts, then a summary"
    assert model.calls.count("check") == 0


def test_zone_and_emerging_lines_are_parsed_marked_and_kept(root, model, sam, wx, backend):
    add_photos(root)
    model.reading = model.reading + [
        {"key": "zone", "where": "S edge", "what": "the cut strip: stubble and bare silt", "photos": [2],
         "confidence": 0.7},
        {"key": "zone", "where": "NW corner", "what": "ogi stand, head-high", "photos": [1], "confidence": 0.6},
        {"key": "emerging", "name": "ヘアリーベッチ", "scientific": "Vicia villosa", "where": "S edge",
         "photos": [2], "confidence": 0.5}]
    rec = pipeline.run_observation(FIELD, DAY, root, backend)
    assert [o.key for o in rec.observations] == ["overall", "dominant", "acidity", "zone", "zone", "emerging", "animal"]
    zone, zone2, emerging = rec.observations[3:6]
    assert zone.text == "S edge: the cut strip: stubble and bare silt (photos 2) [0.70]"
    assert emerging.text == "ヘアリーベッチ (Vicia villosa) at S edge (photos 2) [0.50]"

    pipeline.mark(FIELD, DAY, "zone#2", "wrong", "that is goldenrod", root=root)
    pipeline.mark(FIELD, DAY, "emerging", "right", root=root)
    rec = pipeline.run_observation(FIELD, DAY, root, backend)  # a re-run keeps the marks
    assert [(o.key, o.verdict) for o in rec.observations if o.key in ("zone", "emerging")] == [
        ("zone", None), ("zone", "wrong"), ("emerging", "right")]

    text = timeline.timeline(FIELD, root / "records")
    assert "zone: NW corner: ogi stand, head-high (photos 1) [0.60]  → farmer: wrong (that is goldenrod)" in text
    assert "## Coming up day by day" in text
    assert "| ヘアリーベッチ (Vicia villosa) | S edge (photos 2) ✓ |" in text


def test_sowing_from_earlier_work_lines_goes_into_the_prompt(root, model, sam, wx, backend):
    from fieldnotes.records import Observation
    Record(FIELD, "2026-10-27", voice=[Observation("work", "刈った帯に10種を混播した"),
                                        Observation("work", "間違い", "wrong")]).save(root / "records")
    add_photos(root)
    pipeline.run_observation(FIELD, DAY, root, backend)
    texts = _texts(model.messages["describe"][0])
    history = next(t for t in texts if t.startswith("What the farmer did on this field before today"))
    assert "- 2026-10-27: 刈った帯に10種を混播した" in history and "間違い" not in history
