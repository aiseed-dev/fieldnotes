from __future__ import annotations

from datetime import date, timedelta

import pytest
from conftest import DAY, FIELD, add_photos
from PIL import Image

from fieldnotes import describe, pipeline, weather
from fieldnotes.records import Observation, Record


def line(rec: Record, key: str) -> Observation:
    return next(o for o in rec.observations if o.key == key)


# ---- a whole observation ------------------------------------------------

def test_run_observation_end_to_end(root, model, sam, wx, backend):
    add_photos(root)
    steps: list[str] = []

    rec = pipeline.run_observation(FIELD, DAY, root, backend, progress=steps.append)

    assert rec.field == FIELD and rec.date == "2026-10-28"
    assert rec.photos == [f"photos/{FIELD}/2026-10-28/080000-a.jpg", f"photos/{FIELD}/2026-10-28/081500-b.jpg"]
    assert rec.weather["days_since_rain"] == 1
    assert rec.ai_model == "fake-model"
    assert [o.key for o in rec.observations] == ["overall", "dominant", "acidity", "animal"]
    assert rec.coverage == {"bare soil": 25.0}  # first day: only the base noun was known when SAM ran
    assert len(steps) >= 6

    # the saved file is what was returned, and a person can read it
    path = root / "records" / FIELD / "2026-10-28.md"
    assert Record.load(root / "records", FIELD, "2026-10-28") == rec
    assert "## AI observation (fake-model)" in path.read_text(encoding="utf-8")

    # one overlay per photo, same size as the photo
    overlays = pipeline.overlay_paths(FIELD, DAY, root)
    assert [p.name for p in overlays] == ["2026-10-28-overlay-1.jpg", "2026-10-28-overlay-2.jpg"]
    with Image.open(overlays[0]) as im:
        assert im.size == (64, 48)

    # step 7: today's dominant plant got a SAM noun for next time, and its ecology was looked up
    assert "goldenrod | for: セイタカアワダチソウ (Solidago altissima)" in (
        root / "records" / "_concepts" / f"{FIELD}.md").read_text(encoding="utf-8")
    assert (root / "records" / "_plants" / "Solidago_altissima.md").exists()


def test_second_day_uses_the_first(root, model, sam, wx, backend):
    add_photos(root)
    pipeline.run_observation(FIELD, DAY, root, backend)
    nxt = DAY + timedelta(days=1)
    add_photos(root, day=nxt, names=("090000-c",))

    rec = pipeline.run_observation(FIELD, nxt, root, backend)

    assert rec.coverage == {"bare soil": 25.0, "goldenrod": 50.0}
    assert sam.calls[-1] == ("090000-c.jpg", ["bare soil", "goldenrod"])
    # describe saw the earlier day's two photos and today's one
    user = model.messages["describe"][-1][1]["content"]
    assert sum(p["type"] == "image_url" for p in user) == 3
    assert "goldenrod" in (root / "records" / "_concepts" / f"{FIELD}.md").read_text(encoding="utf-8")


def test_no_photos_and_bad_field(root, model, sam, wx, backend):
    with pytest.raises(FileNotFoundError):
        pipeline.run_observation(FIELD, DAY, root, backend)
    with pytest.raises(ValueError):
        pipeline.run_observation("../etc", DAY, root, backend)
    assert not model.calls and not sam.calls


def test_missing_weather_does_not_stop_the_reading(root, model, sam, backend, monkeypatch):
    def no_weather(*a, **k):
        raise KeyError("no weather for 2026-10-28 yet")

    monkeypatch.setattr(weather, "daily_weather", no_weather)
    add_photos(root)
    steps: list[str] = []
    rec = pipeline.run_observation(FIELD, DAY, root, backend, progress=steps.append)
    assert rec.weather == {} and rec.observations
    assert any("天気は取れませんでした" in s for s in steps)


# ---- re-running keeps the farmer's work ---------------------------------

def test_rerun_keeps_verdicts_note_and_earlier_lines(root, model, sam, wx, backend):
    add_photos(root)
    pipeline.run_observation(FIELD, DAY, root, backend)
    pipeline.mark(FIELD, DAY, "dominant", "right", root=root)
    pipeline.mark(FIELD, DAY, "overall", "wrong", "it is uneven, not even", root=root)
    rec = Record.load(root / "records", FIELD, DAY.isoformat())
    rec.farmer_note, rec.note_model = "north end was cut last week", "muse-voice"
    rec.save(root / "records")

    # second reading: overall says something else; dominant is the same words with another confidence
    model.reading[0]["text"] = "Uneven, with tall goldenrod in the north."
    model.reading[1]["confidence"] = 0.9
    again = pipeline.run_observation(FIELD, DAY, root, backend)

    assert line(again, "dominant").verdict == "right"
    assert line(again, "dominant").text.endswith("[0.90]")  # the new confidence, the old verdict
    assert line(again, "overall").verdict is None
    assert line(again, "overall").text.startswith("Uneven, with tall goldenrod")
    assert [(o.key, o.verdict, o.reason) for o in again.earlier] == [
        ("overall", "wrong", "it is uneven, not even")]
    assert again.earlier[0].text.startswith("Even green cover")
    assert again.farmer_note == "north end was cut last week" and again.note_model == "muse-voice"
    text = (root / "records" / FIELD / "2026-10-28.md").read_text(encoding="utf-8")
    assert text.index("## AI observation") < text.index("## Earlier AI lines") < text.index("## Farmer note")

    # a third run with the same reading adds nothing to the earlier lines
    third = pipeline.run_observation(FIELD, DAY, root, backend)
    assert [(o.key, o.text) for o in third.earlier] == [(o.key, o.text) for o in again.earlier]
    assert line(third, "dominant").verdict == "right"


def test_rerun_with_fewer_photos_drops_stale_overlays(root, model, sam, wx, backend):
    d = add_photos(root)
    pipeline.run_observation(FIELD, DAY, root, backend)
    (d / "081500-b.jpg").unlink()
    pipeline.run_observation(FIELD, DAY, root, backend)
    assert [p.name for p in pipeline.overlay_paths(FIELD, DAY, root)] == ["2026-10-28-overlay-1.jpg"]


def test_merge_rerun_unit():
    old = Record(FIELD, "2026-10-28", farmer_note="n", note_model="m", earlier=[Observation("soil", "old", "wrong", "r")])
    old.observations = [Observation("overall", "A [0.50]", "right"), Observation("crops", "B", None),
                        Observation("soil", "C", "wrong", "dry")]
    new = Record(FIELD, "2026-10-28")
    new.observations = [Observation("overall", "A [0.70]"), Observation("crops", "B2")]

    out = pipeline.merge_rerun(new, old)

    assert out.observations[0].verdict == "right"
    assert out.observations[1].verdict is None
    assert [(o.key, o.text) for o in out.earlier] == [("soil", "old"), ("soil", "C")]  # unmarked "B" is just replaced
    assert out.farmer_note == "n"


def test_record_round_trip_with_earlier():
    rec = Record(FIELD, "2026-10-28", ai_model="x", observations=[Observation("overall", "now")],
                 earlier=[Observation("overall", "then", "wrong", "no (really)")], note_model="m", farmer_note="note")
    back = Record.from_markdown(rec.to_markdown())
    assert back == rec
    assert "## Earlier AI lines" not in Record(FIELD, "2026-10-28").to_markdown()


# ---- mark ---------------------------------------------------------------

def test_mark(root):
    rec = Record(FIELD, "2026-10-28", ai_model="x", farmer_note="keep me", observations=[
        Observation("overall", "o"), Observation("other", "first"), Observation("other", "second")])
    rec.save(root / "records")

    got = pipeline.mark(FIELD, DAY, "overall", "wrong", "too\nsimple", root=root)
    assert (got.verdict, got.reason) == ("wrong", "too simple")
    pipeline.mark(FIELD, "2026-10-28", "other#2", "right", root=root)  # an ISO string works too
    back = Record.load(root / "records", FIELD, "2026-10-28")
    assert [(o.key, o.text, o.verdict, o.reason) for o in back.observations] == [
        ("overall", "o", "wrong", "too simple"), ("other", "first", None, None), ("other", "second", "right", None)]
    assert back.farmer_note == "keep me"

    pipeline.mark(FIELD, DAY, "overall", None, root=root)  # clearing
    assert Record.load(root / "records", FIELD, "2026-10-28").observations[0].verdict is None
    # a reason without a verdict is not kept
    assert Record.load(root / "records", FIELD, "2026-10-28").observations[0].reason is None


def test_mark_errors(root):
    Record(FIELD, "2026-10-28", observations=[Observation("overall", "o")]).save(root / "records")
    with pytest.raises(KeyError):
        pipeline.mark(FIELD, DAY, "crops", "right", root=root)
    with pytest.raises(KeyError):
        pipeline.mark(FIELD, DAY, "overall#2", "right", root=root)
    with pytest.raises(ValueError):
        pipeline.mark(FIELD, DAY, "overall", "maybe", root=root)
    with pytest.raises(FileNotFoundError):
        pipeline.mark(FIELD, date(2026, 1, 1), "overall", "right", root=root)
    with pytest.raises(ValueError):
        pipeline.mark("../x", DAY, "overall", "right", root=root)


# ---- fields side by side ------------------------------------------------

def test_compare_latest(root, model, sam, wx, backend):
    for f in ("uncut", "row1"):
        add_photos(root, field=f, names=("080000-a",))
        pipeline.run_observation(f, DAY, root, backend)

    rec = pipeline.compare_latest(DAY, root, backend)

    assert rec.field == describe.COMPARE and rec.date == "2026-10-28"
    assert [o.key for o in rec.observations] == ["overall", "fertility"]
    assert "row1 (moderate) > uncut (moderate)" in line(rec, "fertility").text
    pipeline.mark(describe.COMPARE, DAY, "overall", "right", root=root)
    again = pipeline.compare_latest(DAY, root, backend)
    assert line(again, "overall").verdict == "right"  # same words, verdict kept
    assert (root / "records" / "_compare" / "2026-10-28.md").exists()


def test_compare_needs_two_fields(root, model, sam, wx, backend):
    add_photos(root)
    pipeline.run_observation(FIELD, DAY, root, backend)
    with pytest.raises(ValueError):
        pipeline.compare_latest(DAY, root, backend)
