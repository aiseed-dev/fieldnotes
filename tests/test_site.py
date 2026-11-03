"""Any farm: the place comes from records/site.md, not from the code."""

from fieldnotes import cli, describe, site, surroundings
from fieldnotes.records import Record


def test_init_writes_a_site_profile_that_fills_the_prompts(tmp_path, capsys):
    root = str(tmp_path)
    assert cli.main(["--root", root, "init", "--place", "Nakuru, Kenya", "--country", "ke",
                     "--lat", "-0.30", "--lon", "36.07", "--climate", "highland, two rainy seasons"]) == 0
    s = site.Site.load(tmp_path / "records")
    assert (s.place, s.country, s.lat, s.lon) == ("Nakuru, Kenya", "KE", -0.30, 36.07)
    msgs = describe.build_messages(Record(field="a", date="2026-10-28"), [], tmp_path, place=s)
    assert "a field in Nakuru, Kenya (highland, two rainy seasons; how the farm is worked: not recorded yet)" \
        in msgs[0]["content"]
    assert "Tokushima" not in msgs[0]["content"] and "natural-farming" not in msgs[0]["content"]
    assert "method: not recorded yet" in (tmp_path / "records" / "site.md").read_text(encoding="utf-8")
    # a second init must not overwrite the farmer's notes
    assert cli.main(["--root", root, "init", "--place", "X", "--country", "KE", "--lat", "0", "--lon", "0"]) == 1
    assert "もうあります" in capsys.readouterr().err


def test_a_farm_without_site_md_still_reads():
    s = site.Site()
    assert not s.located
    assert s.fill("You observe <FIELD>; sow in <REGION>.") == \
        "You observe a field (how the farm is worked: not recorded yet); sow in the farmer's region."


def test_the_method_is_the_farms_own_words_not_the_apps(tmp_path):
    """2026-11-03: the app has no method of its own; the prompt carries only what site.md says."""
    assert site.METHOD == ""
    (tmp_path / "records").mkdir()
    (tmp_path / "records" / "site.md").write_text(
        "---\nplace: Rokuse, Tokushima, Japan\ncountry: JP\nlat: 34.08\nlon: 134.44\n"
        "method: former paddy, a pan at about 20 cm to be broken; no pesticide\n---\n", encoding="utf-8")
    assert site.Site.load(tmp_path / "records").field() == \
        "a field in Rokuse, Tokushima, Japan (former paddy, a pan at about 20 cm to be broken; no pesticide)"
    # the line init writes before the farmer has said anything counts as no method
    (tmp_path / "records" / "site.md").write_text("---\nplace: X\nmethod: Not recorded yet\n---\n",
                                                  encoding="utf-8")
    assert site.Site.load(tmp_path / "records").method == ""
    assert "method: no tillage" not in site.template("X", "JP", 34.0, 134.0)


def test_maps_follow_the_country():
    assert surroundings.layers_for(site.Site(country="JP")) == surroundings.JAPAN
    assert surroundings.layers_for(site.Site(country="KE")) == ["osm"]
    assert surroundings.attribution(["osm"]) == "© OpenStreetMap contributors"


def test_init_rejects_bad_coordinates(tmp_path):
    assert cli.main(["--root", str(tmp_path), "init", "--place", "X", "--country", "JPN",
                     "--lat", "34", "--lon", "134"]) == 1
    assert not (tmp_path / "records" / "site.md").exists()
