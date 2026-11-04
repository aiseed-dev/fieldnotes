"""The phone app's views build without a browser: each is constructed with a stub page,
so a control or colour that Flet 1.0.5 does not have fails here, not on the phone.
No network, no model; what the views show is tested in test_appdata.py."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

flet = pytest.importorskip("flet")


class StubPage:
    width, height = 360, 640
    services: list = []

    def update(self):
        pass

    def get_upload_url(self, name, seconds):
        return "http://x/" + name


@pytest.fixture
def app(tmp_path, monkeypatch):
    """fieldnotes.app bound to a scratch farm folder."""
    monkeypatch.setenv("FIELDNOTES_ROOT", str(tmp_path))
    import fieldnotes.app as module
    importlib.reload(module)
    (tmp_path / "records").mkdir(exist_ok=True)
    return module


def test_walk_strip_builds_with_and_without_gps(app, tmp_path):
    from test_walk import parcel, walk_photos
    from fieldnotes.ui import Words
    w = Words("en")
    dialogs = app.Dialogs(StubPage(), w)
    none = app.walk_strip(StubPage(), dialogs, w, "uncut", "2026-10-28")
    assert none.controls[0].value == "No photos for this day yet"
    parcel(tmp_path)
    walk_photos(tmp_path)
    strip = app.walk_strip(StubPage(), dialogs, w, "uncut", "2026-10-28")
    assert strip.controls[0].value == "3 photo(s), 3 with GPS (on the parcel outline)"
    assert len(strip.controls[-1].controls) == 3  # the thumbnails


def test_every_view_builds(app, tmp_path):
    """Send, Read and Nouns are built as build() builds them, on a farm with one read day."""
    from test_walk import parcel, walk_photos
    from fieldnotes.records import Observation, Record
    from fieldnotes.ui import Words
    parcel(tmp_path)
    walk_photos(tmp_path)
    Record(field="uncut", date="2026-10-28", photos=["a"], ai_model="muse-spark-1.3",
           observations=[Observation("overall", "x [0.8]")]).save(tmp_path / "records")
    page, w = StubPage(), Words("ja")
    dialogs = app.Dialogs(page, w)
    send = app.send_view(page, dialogs, w, "ja")
    read, refresh_read = app.read_view(page, dialogs, w, "ja")
    nouns, refresh_nouns = app.nouns_view(page, dialogs, w)
    refresh_read()
    refresh_nouns()
    assert send.controls and read.controls and nouns.controls


def test_land_view_builds_on_an_empty_farm_and_a_farm_with_checks(app, tmp_path):
    """土地: no site.md says so; with site.md and checks the lines and the table are drawn."""
    from test_appdata import land_farm
    from fieldnotes.ui import Words
    page, w = StubPage(), Words("en")
    dialogs = app.Dialogs(page, w)
    view, refresh = app.land_view(page, dialogs, w)
    refresh()
    texts = [getattr(c, "value", None) for c in view.controls[3].controls]
    assert "No site.md: nothing is written about this land yet." in texts
    land_farm(tmp_path)
    refresh()
    assert any(getattr(c, "value", "") == "About this land (site.md)" for c in view.controls[3].controls)


def test_hypotheses_table_and_read_state(app, tmp_path):
    """The Land view's table has a row per hypothesis and a column per day; Read on a day with
    no reading says so."""
    from test_appdata import jpg, land_farm
    from fieldnotes.ui import Words
    land_farm(tmp_path)
    page, w = StubPage(), Words("en")
    dialogs = app.Dialogs(page, w)
    head, row = app.hypotheses_table(dialogs, w, "north").controls
    assert head.value == "Read by: 11-01 m, 11-02 m"
    table = row.controls[0]
    assert len(table.rows) == 1 and len(table.columns) == 3
    assert app.hypotheses_table(dialogs, w, "south").value == "south: no day has checked a hypothesis yet"
    jpg(tmp_path / "photos" / "north" / "2026-11-04" / "100000-a.jpg")
    read, refresh = app.read_view(page, dialogs, w, "en")
    refresh()
    texts = [getattr(c, "value", None) for c in read.controls[-2].controls]
    assert "No reading yet. Press Read and the AI reads the day." in texts


def test_land_tools_offer_init_then_note_and_field_work(app, tmp_path):
    """No site.md: the form to start the land; after it, the note form and the field buttons.
    No button that calls a model is pressed here."""
    from test_appdata import land_farm
    from fieldnotes.ui import Words
    page, w = StubPage(), Words("en")
    tools, refresh = app.land_tools(page, app.Dialogs(page, w), w, "en", lambda: None)
    refresh()
    box = tools.controls[1]
    assert len(box.controls) == 2  # the init form and "no field yet"
    assert box.controls[1].value == "No field has photos or records yet"
    land_farm(tmp_path)
    refresh()
    assert isinstance(box.controls[0], app.ft.ExpansionTile)
    assert len(box.controls) == 8
