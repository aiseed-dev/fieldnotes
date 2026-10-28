from __future__ import annotations

import os
import tomllib
from pathlib import Path

import pytest
from conftest import DAY, FIELD, add_photos
from PIL import Image

from fieldnotes import cli, pipeline, surroundings
from fieldnotes.records import Record

D = DAY.isoformat()


def run(root, *argv) -> int:
    return cli.main(["--root", str(root), *argv])


@pytest.fixture
def observed(root, model, sam, wx):
    """A field with one observation made through the CLI."""
    add_photos(root)
    assert run(root, "observe", FIELD, D) == 0
    return root


def test_observe(root, model, sam, wx, capsys):
    add_photos(root)
    assert run(root, "observe", FIELD, D) == 0
    out = capsys.readouterr()
    assert "## AI observation (muse-spark-1.3)" in out.out
    assert "保存しました" in out.err
    assert (root / "records" / FIELD / f"{D}.md").exists()


def test_observe_defaults_to_today(root, model, sam, wx):
    from datetime import date
    add_photos(root, day=date.today())
    assert run(root, "observe", FIELD) == 0
    assert (root / "records" / FIELD / f"{date.today().isoformat()}.md").exists()


def test_observe_without_photos_is_an_error_not_a_traceback(root, model, sam, wx, capsys):
    assert run(root, "observe", FIELD, D) == 1
    assert "エラー" in capsys.readouterr().err


def test_show(observed, capsys):
    capsys.readouterr()
    assert run(observed, "show", FIELD, D) == 0
    assert "- overall:" in capsys.readouterr().out
    assert run(observed, "show", FIELD) == 0  # no date: the latest
    assert "- overall:" in capsys.readouterr().out
    assert run(observed, "show", "nowhere") == 1


def test_mark(observed, capsys):
    capsys.readouterr()
    assert run(observed, "mark", FIELD, D, "overall", "wrong", "too", "tidy") == 0
    assert "→ farmer: wrong (too tidy)" in capsys.readouterr().out
    assert pipeline.latest_record(FIELD, observed).observations[0].reason == "too tidy"
    assert run(observed, "mark", FIELD, D, "nokey", "right") == 1
    with pytest.raises(SystemExit):
        run(observed, "mark", FIELD, D, "overall", "maybe")


def test_concept(observed, capsys):
    assert run(observed, "concept", FIELD, "goldenrod", "wrong", "finds ogi too", "--replace", "yellow flowers") == 0
    text = (observed / "records" / "_concepts" / f"{FIELD}.md").read_text(encoding="utf-8")
    assert "goldenrod" in text and "→ farmer: wrong (finds ogi too)" in text
    assert "yellow flowers | for: セイタカアワダチソウ (Solidago altissima) | by: farmer" in text
    shared = (observed / "shared" / "sam_concepts.md").read_text(encoding="utf-8")  # tallied under the root, not the cwd
    assert "goldenrod | for: Solidago altissima | right: 0 | wrong: 1" in shared
    assert run(observed, "concept", FIELD, "no such noun", "right") == 1


def test_propose(observed, model, capsys):
    assert run(observed, "propose", FIELD, "--seeds", "crimson clover, rye") == 0
    out = capsys.readouterr().out
    assert "クリムソンクローバー" in out
    files = list((observed / "records" / "_proposals" / FIELD).glob("*-cover_crop.md"))
    assert len(files) == 1 and "crimson clover" in files[0].read_text(encoding="utf-8")
    assert "Seeds on hand: crimson clover, rye" in model.messages["propose"][-1][1]["content"]
    assert run(observed, "propose", "nowhere") == 1


def test_compare(root, model, sam, wx, capsys):
    for f in ("uncut", "row1"):
        add_photos(root, field=f, names=("080000-a",))
        assert run(root, "observe", f, D) == 0
    capsys.readouterr()
    assert run(root, "compare", D) == 0
    assert "fertility:" in capsys.readouterr().out
    assert (root / "records" / "_compare" / f"{D}.md").exists()


def test_compare_with_one_field_is_an_error(observed, capsys):
    assert run(observed, "compare", D) == 1
    assert "エラー" in capsys.readouterr().err


def test_surroundings(root, model, monkeypatch, capsys):
    def fake_fetch(records):
        d = records / "surroundings"
        d.mkdir(parents=True, exist_ok=True)
        out = {}
        for layer in surroundings.LAYERS:
            Image.new("RGB", (32, 32), "green").save(d / f"{layer}.jpg")
            out[layer] = d / f"{layer}.jpg"
        return out

    monkeypatch.setattr(surroundings, "fetch_maps", fake_fetch)
    assert run(root, "surroundings") == 0
    assert "paddies to the south" in capsys.readouterr().out
    assert model.calls.count("surroundings") == 1
    # once: a second call must not read again and lose the farmer's marks
    assert run(root, "surroundings") == 0
    assert model.calls.count("surroundings") == 1
    assert "すでに読んであります" in capsys.readouterr().err
    assert run(root, "surroundings", "--force") == 0
    assert model.calls.count("surroundings") == 2


def test_app(root, monkeypatch):
    from fieldnotes import app
    served = {}
    monkeypatch.setattr(app, "run", lambda port: served.update(port=port))
    monkeypatch.delenv("FIELDNOTES_ROOT")
    assert run(root, "app", "--port", "9000") == 0
    assert served == {"port": 9000}
    assert Path(os.environ["FIELDNOTES_ROOT"]) == root.resolve()
    os.environ.pop("FIELDNOTES_ROOT")


def test_console_script_is_declared():
    meta = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["scripts"]["fieldnotes"] == "fieldnotes.cli:main"
