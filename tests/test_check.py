"""Hypotheses checked on photos: expectations written first (text only), then each day's photos."""

from __future__ import annotations

from conftest import DAY, FIELD, add_photos

from fieldnotes import check, cli, pipeline, timeline
from fieldnotes.records import Record

SITE = """---
place: Tokushima, Japan
country: JP
lat: 34.08
lon: 134.44
---

# Site profile

- `hypothesis` — a reading of the field, by the farmer or by the AI, not yet checked.

## Terrain

- `hypothesis` The silt holds water after rain. — farmer
- `data` Elevation 7 m.
- `hypothesis` The soil was laid by a flood 2000 years ago. — farmer
- `hypothesis` Ogi spreads from the river bank. — AI

## How a hypothesis is checked

- `hypothesis` an example in the how-to, not a claim
"""


def farm(root):
    (root / "records").mkdir(parents=True, exist_ok=True)
    (root / "records" / "site.md").write_text(SITE, encoding="utf-8")
    add_photos(root)
    return root / "records"


def test_hypotheses_in_file_order_without_the_legend_or_the_how_to(root):
    records = farm(root)
    assert check.hypotheses(records) == ["The silt holds water after rain. — farmer",
                                         "The soil was laid by a flood 2000 years ago. — farmer",
                                         "Ogi spreads from the river bank. — AI"]


def test_expectations_are_written_from_text_alone(root, model, backend):
    records = farm(root)
    path = check.expect(FIELD, root, backend, "2026-10-30")
    assert path == records / "_checks" / FIELD / "expect.md"
    front, lines = check.load(records, FIELD)
    assert front["field"] == FIELD and front["model"] == "fake-model" and front["date"] == "2026-10-30"
    assert front["hypotheses"]["h2"] == "The soil was laid by a flood 2000 years ago. — farmer"
    assert [o.to_line() for o in lines] == [
        "- h1: holds: sign 1 present, dense; fails: sign 1 absent; visible: yes [0.60]",
        "- h2: holds: sign 2 present, dense; fails: sign 2 absent; visible: no [0.60]",
        "- h3: holds: sign 3 present, dense; fails: sign 3 absent; visible: yes [0.60]"]
    sent = model.messages["expect"][0][1]["content"]
    assert isinstance(sent, str) and "photo" not in model.calls  # no image in the call


def test_observe_adds_checks_in_a_call_of_its_own(root, model, sam, wx, backend):
    records = farm(root)
    check.expect(FIELD, root, backend)
    check.mark(records, FIELD, "h3", "wrong", "ogi came with the soil, not from the bank")

    rec = pipeline.run_observation(FIELD, DAY, root, backend)

    assert model.calls.index("check") > model.calls.index("describe")
    # h2 cannot be seen and h3 was marked wrong: neither is checked, whatever the model says
    assert [o.to_line() for o in rec.checks] == ["- h1: agrees: what h1 looks like [0.50]"]
    sent = model.messages["check"][0][1]["content"]
    assert sum(p["type"] == "image_url" for p in sent) == 2
    assert "Even green cover" not in "\n".join(p["text"] for p in sent if p["type"] == "text")  # not the reading
    text = (records / FIELD / "2026-10-28.md").read_text(encoding="utf-8")
    assert "## Checks (fake-model)\n- h1: agrees: what h1 looks like [0.50]" in text


def test_a_rerun_keeps_the_farmers_marks_on_checks(root, model, sam, wx, backend):
    records = farm(root)
    check.expect(FIELD, root, backend)
    pipeline.run_observation(FIELD, DAY, root, backend)
    pipeline.mark(FIELD, DAY, "h1", "right", root=root)
    rec = pipeline.run_observation(FIELD, DAY, root, backend)
    assert rec.checks[0].verdict == "right"
    assert Record.load(records, FIELD, DAY.isoformat()).checks[0].to_line().endswith("→ farmer: right")


def test_timeline_puts_each_hypothesis_in_a_row(root, model, sam, wx, backend):
    records = farm(root)
    check.expect(FIELD, root, backend)
    pipeline.run_observation(FIELD, DAY, root, backend)
    pipeline.mark(FIELD, DAY, "h1", "right", root=root)
    out = timeline.timeline(FIELD, records)
    assert "checks: h1 agrees ✓" in out
    assert "| hypothesis | 2026-10-28 |" in out and "| h1 The silt holds water after rain. — farmer | agrees ✓ |" in out


def test_no_expectations_no_checks(root, model, sam, wx, backend):
    farm(root)
    rec = pipeline.run_observation(FIELD, DAY, root, backend)
    assert rec.checks == [] and "check" not in model.calls


def test_the_farmer_marks_an_expectation_from_the_cli(root, model, backend):
    records = farm(root)
    check.expect(FIELD, root, backend)
    assert cli.main(["--root", str(root), "mark", FIELD, "2026-10-30", "h1", "wrong", "too", "vague",
                     "--proposal", "expect"]) == 0
    assert check.load(records, FIELD)[1][0].to_line().endswith("→ farmer: wrong (too vague)")
    assert "h1" not in check.to_check(records, FIELD)
