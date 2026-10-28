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
    assert "a natural-farming field in Nakuru, Kenya (highland, two rainy seasons;" in msgs[0]["content"]
    assert "Tokushima" not in msgs[0]["content"]
    # a second init must not overwrite the farmer's notes
    assert cli.main(["--root", root, "init", "--place", "X", "--country", "KE", "--lat", "0", "--lon", "0"]) == 1
    assert "もうあります" in capsys.readouterr().err


def test_a_farm_without_site_md_still_reads():
    s = site.Site()
    assert not s.located
    assert s.fill("You observe <FIELD>; sow in <REGION>.") == \
        f"You observe a natural-farming field ({site.METHOD}); sow in the farmer's region."


def test_maps_follow_the_country():
    assert surroundings.layers_for(site.Site(country="JP")) == surroundings.JAPAN
    assert surroundings.layers_for(site.Site(country="KE")) == ["osm"]
    assert surroundings.attribution(["osm"]) == "© OpenStreetMap contributors"


def test_init_rejects_bad_coordinates(tmp_path):
    assert cli.main(["--root", str(tmp_path), "init", "--place", "X", "--country", "JPN",
                     "--lat", "34", "--lon", "134"]) == 1
    assert not (tmp_path / "records" / "site.md").exists()
