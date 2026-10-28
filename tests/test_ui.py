"""The screen and CLI words (ui.py) in Japanese and English; no Flet, no network."""

import re
import string

from fieldnotes import appdata, cli, concepts, llm, ui
from fieldnotes.inbox import AROUND


def test_every_text_has_both_languages_with_the_same_fields():
    fields = lambda t: {f for _, f, _, _ in string.Formatter().parse(t) if f}
    for key, (ja, en) in ui.TEXTS.items():
        assert ja and en, key
        assert fields(ja) == fields(en), key
        assert not re.search(r"[぀-ヿ一-鿿]", en), key  # no Japanese left in the English


def test_screen_follows_the_ai_language():
    assert ui.Words("ja")("nav.read") == "読む"
    assert ui.Words("en")("nav.read") == "Read"
    assert ui.Words("fr").lang == "en"  # no French screen yet: English
    assert ui.Words("en")("send.placed", n=3, field="uncut") == "Filed under uncut: 3 photo(s)"


def test_labels_in_english():
    w = ui.Words("en")
    assert appdata.key_label("dominant", w) == "Dominant plants"
    assert appdata.key_label("made_up", w) == "made_up"
    assert appdata.place_label(AROUND, w) == "Neighbourhood (around the fields)"
    assert appdata.last_label("-", w) == "not used yet"
    assert appdata.last_label("2026-10-28 23.4%, 12 objects", w) == "2026-10-28 23.4%, 12 objects"


def test_default_nouns_are_described_in_the_language_in_use(tmp_path):
    llm.set_language("en")
    targets = {c.noun: c.target for c in concepts.FieldConcepts.load(tmp_path, "row1").items}
    assert targets["bare soil"] == "bare soil" and targets["leaf"] == "leaves (crops and weeds)"


def test_cli_in_english(monkeypatch, capsys):
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert cli.main(["consent"]) == 0
    out = capsys.readouterr().out
    assert "Use for AI training: not decided yet" in out
    assert cli.main(["show", "nowhere"]) != 0
    assert "Error: No record for nowhere" in capsys.readouterr().err
