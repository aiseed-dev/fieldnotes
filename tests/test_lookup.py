"""Public data for any farm, offline: the services are faked at lookup.get_json."""

import json

from fieldnotes import cli, lookup

ANSWERS = {
    "open-meteo.com": {"elevation": [5.0]},
    "macrostrat.org": {"success": {"data": [{"name": "Cenozoic volcanic rocks", "lith": "phonolite", "descrip": "",
                                             "b_int_name": "Neogene", "t_int_name": "Neogene", "scale": "tiny"}]}},
    "isric.org": {"properties": {"layers": [{"name": "phh2o", "depths": [{"label": "0-5cm", "values": {"mean": 65}}]}]}},
    "wikipedia.org": {"query": {"geosearch": [{"title": "Lake Nakuru", "lat": -0.35, "lon": 36.08, "dist": 5600}],
                                "search": [{"title": "Nakuru Fort"}]}},
    "overpass": {"elements": [{"type": "node", "id": 1, "lat": -0.29, "lon": 36.07,
                               "tags": {"historic": "archaeological_site", "name": "Hyrax Hill"}}]},
}


def fake(url, data=None, timeout=60, tries=3):
    if "gsj.jp" in url:
        raise ValueError("maintenance")
    return next(v for k, v in ANSWERS.items() if k in url)


def init(tmp_path, country="KE"):
    assert cli.main(["--root", str(tmp_path), "init", "--place", "Nakuru, Kenya", "--country", country,
                     "--lat", "-0.30", "--lon", "36.07"]) == 0


def test_lookup_writes_sourced_lines(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lookup, "get_json", fake)
    init(tmp_path)
    assert cli.main(["--root", str(tmp_path), "lookup"]) == 0
    text = (tmp_path / "records" / "lookup.md").read_text()
    assert "`data` Elevation 5 m." in text
    assert "Bedrock: Cenozoic volcanic rocks; phonolite (Neogene" in text
    assert "Soil pH (water): 0-5cm 6.5" in text
    assert "`reference` Hyrax Hill (archaeological_site, 1.1 km N)" in text
    assert "`reference` Lake Nakuru (5.6 km S)" in text
    assert "GSJ" not in text  # the Japanese geology map is asked only in Japan
    assert json.loads((tmp_path / "records" / "lookup" / "soil.json").read_text())


def test_a_source_that_is_down_is_named_not_fatal(tmp_path, monkeypatch):
    monkeypatch.setattr(lookup, "get_json", fake)
    init(tmp_path, "JP")
    lookup.lookup(tmp_path / "records")
    text = (tmp_path / "records" / "lookup.md").read_text()
    assert "(GSJ シームレス地質図: not reached on" in text and "Elevation 5 m" in text


def test_search_near_the_farm_and_save(tmp_path, monkeypatch, capsys):
    asked = []
    monkeypatch.setattr(lookup, "get_json", lambda url, data=None, **kw: asked.append((url, data)) or fake(url))
    init(tmp_path)
    lookup.lookup(tmp_path / "records")
    capsys.readouterr()
    assert cli.main(["--root", str(tmp_path), "search", "fort", "--save"]) == 0
    assert "Nakuru Fort" in capsys.readouterr().out
    assert any("nearcoord%3A10km%2C-0.3%2C36.07" in u for u, _ in asked)
    assert "## Search: fort" in (tmp_path / "records" / "lookup.md").read_text()


def test_busy_wikipedia_is_retried(monkeypatch):
    answers = iter([{"error": {"code": "cirrussearch-too-busy-error"}}, {"query": {}}])
    monkeypatch.setattr(lookup, "get_json", lambda url, **kw: next(answers))
    monkeypatch.setattr(lookup.time, "sleep", lambda s: None)
    assert lookup._wiki("en", action="query") == {"query": {}}
