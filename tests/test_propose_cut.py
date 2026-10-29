"""The cut proposal: where to cut first and how high, from the plot's own records."""

from __future__ import annotations

import json

from conftest import DAY, FIELD, add_photos
from test_cli import D, run

from fieldnotes import propose
from fieldnotes.records import Observation, Record


def test_propose_cut_from_the_cli(root, model, sam, wx, capsys):
    add_photos(root)
    assert run(root, "observe", FIELD, D) == 0
    capsys.readouterr()
    assert run(root, "propose", FIELD, "--cut") == 0
    out = capsys.readouterr().out
    assert "## Cut proposal (muse-spark-1.3)" in out and "- where: the south edge" in out
    files = list((root / "records" / "_proposals" / FIELD).glob("*-cut.md"))
    assert len(files) == 1
    prop = propose.Proposal.from_markdown(files[0].read_text(encoding="utf-8"))
    assert prop.kind == "cut"
    assert [o.key for o in prop.notes] == ["summary", "basis", "where", "height", "leave", "method", "watch"]
    prompt = model.messages["cut"][-1][1]["content"]
    assert "Cover measured by SAM 3.1" in prompt and "goldenrod 50.0%" in prompt  # the fake SAM finds goldenrod


def test_basis_says_when_sam_found_nothing():
    rec = Record(FIELD, "2026-10-28", coverage={"bare soil": 0.0, "silvergrass": 0.0, "goldenrod": 0.0,
                                                 "leaf": 0.0, "flower cluster": 3.1},
                 observations=[Observation("dominant", "オギ (Miscanthus sacchariflorus) ~60%; "
                                                       "セイタカアワダチソウ (Solidago altissima) ~30% [0.80]")])
    basis = propose.cover_basis(rec)
    assert "SAM 3.1 found none of the plants" in basis and "flower cluster 3.1%" in basis
    assert "AI's own reading of the photos: オギ (Miscanthus sacchariflorus) ~60%" in basis
    rec.coverage["goldenrod"] = 12.5
    assert propose.cover_basis(rec).startswith("Cover measured by SAM 3.1")


def test_basis_names_the_plants_sam_did_not_find(tmp_path):
    from fieldnotes.concepts import Concept, FieldConcepts
    fc = FieldConcepts.load(tmp_path, FIELD)
    fc.items += [Concept("silvergrass", "オギ (Miscanthus sacchariflorus)"),
                 Concept("yellow flower clusters", "セイタカアワダチソウ (Solidago altissima)")]
    fc.save(tmp_path)
    rec = Record(FIELD, "2026-10-28", coverage={"silvergrass": 0.0, "yellow flower clusters": 7.2},
                 observations=[Observation("dominant", "オギ (Miscanthus sacchariflorus) ~60%; "
                                                       "セイタカアワダチソウ (Solidago altissima) ~30% [0.80]")])
    basis = propose.cover_basis(rec, tmp_path)
    assert 'セイタカアワダチソウ (Solidago altissima) by "yellow flower clusters" 7.2%' in basis
    assert "no phrase for オギ (Miscanthus sacchariflorus): their shares come only from the AI's own reading" in basis


def test_parse_cut_keeps_every_line_markable():
    text = json.dumps({"summary": {"text": "Cut the edge.", "confidence": 0.5},
                       "leave": [{"text": "ogi", "confidence": 0.4}, {"text": "the wet corner"}],
                       "cautions": [{"text": "goldenrod seeds\nfall", "confidence": 0.3}], "watch": {"text": "regrowth"}})
    assert [o.to_line() for o in propose.parse_cut(text)] == [
        "- summary: Cut the edge. [0.50]", "- leave: ogi [0.40]", "- leave: the wet corner",
        "- watch: regrowth", "- caution: goldenrod seeds fall [0.30]"]


def test_a_rejected_cut_is_not_repeated(root, model, sam, wx, capsys):
    add_photos(root)
    assert run(root, "observe", FIELD, D) == 0
    records = root / "records"
    latest = Record.load(records, FIELD, D)
    propose.propose_cut(latest, "2026-10-29", records, propose.Backend("m", "u", "m", "k"))
    propose.propose_cover_crop(latest, "2026-10-29", records, propose.Backend("m", "u", "m", "k"))
    line = propose.mark(records, FIELD, "2026-10-29", "cut", "height", "wrong", "20 cm leaves the goldenrod to\nseed")
    assert (line.verdict, line.reason) == ("wrong", "20 cm leaves the goldenrod to seed")
    propose.mark(records, FIELD, "2026-10-29", "cover_crop", "summary", "wrong", "not a cut point")
    assert run(root, "mark", FIELD, "2026-10-29", "leave", "right", "--proposal", "cut") == 0
    assert "- leave: the ogi stand on the north side, as a windbreak [0.50]  → farmer: right" in capsys.readouterr().out

    propose.propose_cut(latest, "2026-10-30", records, propose.Backend("m", "u", "m", "k"))
    prompt = model.messages["cut"][-1][1]["content"]
    assert '- height: "20 cm, above the root crowns [0.50]" was wrong: 20 cm leaves the goldenrod to seed' in prompt
    assert "not a cut point" not in prompt  # the cover-crop proposal's marks stay with the cover crop
    assert run(root, "mark", FIELD, "2026-10-29", "where#2", "right", "--proposal", "cut") == 1
    assert run(root, "mark", FIELD, "2026-10-31", "where", "right", "--proposal", "cut") == 1


def test_the_farmers_voice_goes_into_the_proposal(root, model, sam, wx):
    add_photos(root)
    assert run(root, "observe", FIELD, D) == 0
    records = root / "records"
    rec = Record.load(records, FIELD, D)
    rec.voice = [Observation("work", "北側の通路だけ刈った"), Observation("seen", "取り違え", "wrong")]
    rec.save(records)
    propose.propose_cut(Record.load(records, FIELD, D), "2026-10-29", records, propose.Backend("m", "u", "m", "k"))
    prompt = model.messages["cut"][-1][1]["content"]
    assert "- work: 北側の通路だけ刈った" in prompt and "取り違え" not in prompt
