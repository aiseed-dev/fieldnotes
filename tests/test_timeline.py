"""timeline.py: one field day by day, oldest first."""

from __future__ import annotations

from conftest import FIELD

from fieldnotes import propose, timeline
from fieldnotes.records import Observation, Record


def test_days_in_order_with_work_marks_and_proposals(root):
    records = root / "records"
    Record(FIELD, "2026-10-29", photos=["photos/uncut/2026-10-29/0800-a.jpg"], weather={"tmax": 19.0, "rain_mm": 0.0},
           ai_model="muse-spark-1.3",
           observations=[Observation("overall", "Cut strip shows bare silt.", "right"),
                         Observation("dominant", "ogi ~50%", "wrong", "goldenrod is gone from the strip"),
                         Observation("dryness", "dry")],
           voice=[Observation("work", "cut the south strip at 40 cm"), Observation("seen", "ogi shoots", "right")]).save(records)
    Record(FIELD, "2026-10-28", ai_model="muse-spark-1.3", observations=[Observation("overall", "Dense stand.")]).save(records)
    propose.Proposal(FIELD, "2026-10-28", kind="cut", model="m", notes=[
        Observation("summary", "South edge first, 40 cm.", "wrong", "start at the north path"),
        Observation("where", "south edge")]).save(records)
    propose.Proposal(FIELD, "2026-10-30", kind="cover_crop", model="m", notes=[Observation("summary", "Rye and clover.")]).save(records)

    text = timeline.timeline(FIELD, records)
    assert [l for l in text.splitlines() if l.startswith("## ")] == ["## 2026-10-28", "## 2026-10-29", "## 2026-10-30"]
    day28, day29, day30 = text.split("## ")[1:]
    assert "overall: Dense stand." in day28 and "farmer: 0 ✓, 0 ✗ of 1 AI lines (muse-spark-1.3)" in day28
    assert "cut proposal: summary: South edge first, 40 cm.  → farmer: wrong (start at the north path)" in day28
    assert "where:" not in day28  # only the proposal's summary
    assert "photos: photos/uncut/2026-10-29/0800-a.jpg" in day29 and "weather: tmax 19.0, rain_mm 0.0" in day29
    assert "overall: Cut strip shows bare silt.  → farmer: right" in day29
    assert "work: cut the south strip at 40 cm" in day29 and "seen: ogi shoots  → farmer: right" in day29
    assert "farmer: 1 ✓, 1 ✗ of 3 AI lines" in day29
    assert day30.strip() == "2026-10-30\ncover-crop proposal: summary: Rye and clover."
    assert "2026-10-28" not in timeline.timeline(FIELD, records, since="2026-10-29")
