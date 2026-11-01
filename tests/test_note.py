"""What the farmer knows and what a document says, into site.md; offline (the model and GSJ are faked)."""

import json
from datetime import date

from PIL import Image

from fieldnotes import cli, llm, lookup, mcp_server, note
from fieldnotes.llm import Backend
from fieldnotes.site import Site

DAY = date(2026, 11, 2)


def init(tmp_path):
    assert cli.main(["--root", str(tmp_path), "init", "--place", "Tokushima, Japan", "--country", "JP",
                     "--lat", "34.08", "--lon", "134.445"]) == 0
    return tmp_path / "records"


def test_the_farmers_words_and_a_document_go_under_their_sections(tmp_path):
    records = init(tmp_path)
    note.add(records, "history", [note.line("母が蚕を飼っていた。", None, DAY)])
    note.add(records, "history", [note.line("高川原村の桑園 83町（1932年）", "石井町史 p.833", DAY)])
    note.add(records, "geology", [note.line("黒色片岩が風化したシルトで、砂は少ない", None, DAY)])
    note.add(records, "Wells", [note.line("井戸は 6 m", None, DAY)])
    text = (records / "site.md").read_text(encoding="utf-8")
    assert ("## History of the land\n\n- `record` 母が蚕を飼っていた。 — the farmer, 2026-11-02.\n"
            "- `data` 高川原村の桑園 83町（1932年）。 — 石井町史 p.833; noted 2026-11-02.\n\n"
            "## What the farmer knows") in text
    assert "## Geology and soil\n\n- `record` 黒色片岩が風化したシルトで、砂は少ない。 — the farmer, 2026-11-02.\n\n## History" in text
    assert text.endswith("## Wells\n\n- `record` 井戸は 6 m. — the farmer, 2026-11-02.\n")
    (records / "site.md").write_text(text + "\n## How a hypothesis is checked\n\nBy growing.\n", encoding="utf-8")
    note.add(records, "Ponds", [note.line("溜池は埋めた", None, DAY)])
    text = (records / "site.md").read_text(encoding="utf-8")
    assert "## Wells\n\n- `record` 井戸は 6 m. — the farmer, 2026-11-02.\n\n## Ponds\n\n- `record` 溜池は埋めた。" \
           " — the farmer, 2026-11-02.\n\n## How a hypothesis is checked\n\nBy growing.\n" in text


def test_a_page_photo_is_kept_and_copied_out_with_its_source(tmp_path, monkeypatch):
    records = init(tmp_path)
    (records / "lookup").mkdir()
    (records / "lookup" / "address_jp.json").write_text(json.dumps(
        {"results": {"lv01Nm": "高川原"}, "muni": "36,徳島県,36341,石井町"}), encoding="utf-8")
    page = tmp_path / "IMG_1.jpg"
    Image.new("RGB", (3000, 4000), "white").save(page)
    asked = []

    def fake(backend, messages):
        asked.append(messages)
        return '```json\n{"lines": ["高川原村 桑園 83町 (1932年)", "  "]}\n```'
    monkeypatch.setattr(llm, "chat", fake)
    lines = note.read_page(records, page, "石井町史 p.833", DAY, Backend("spark", "x", "muse-spark-1.3", "k"))
    assert lines == ["- `data` 高川原村 桑園 83町 (1932年). — 石井町史 p.833; read from the farmer's photo of the page by "
                     "muse-spark-1.3 (check against the page), documents/2026-11-02-IMG_1.jpg, 2026-11-02."]
    assert (records / "documents" / "2026-11-02-IMG_1.jpg").exists() and page.exists()
    prompt = asked[0][0]["content"][0]["text"]
    assert "石井町 高川原" in prompt and "石井町史 p.833" in prompt


def test_note_from_the_command_line_and_the_farmers_ai(tmp_path, capsys):
    records = init(tmp_path)
    assert cli.main(["--root", str(tmp_path), "note", "飯尾川沿いに桑の木", "--section", "history"]) == 0
    assert "- `record` 飯尾川沿いに桑の木。" in capsys.readouterr().out
    assert cli.main(["--root", str(tmp_path), "note", "--page", "x.jpg"]) == 1
    from test_mcp import call
    _, written, bad = call(mcp_server.build(tmp_path),
                           ("note", {"text": "昔はホウレンソウの産地", "section": "works"}),
                           ("note", {"text": "x", "section": "weather"}))
    assert written.startswith("- `record` 昔はホウレンソウの産地。 — the farmer, ")
    assert bad.startswith("ERROR:") and "section is one of" in bad
    assert "飯尾川沿いに桑の木" in (records / "site.md").read_text(encoding="utf-8")


def test_rocks_around_name_the_first_hard_rock_each_way(monkeypatch):
    schist = {"formationAge_ja": "中生代 白亜紀", "group_ja": "変成岩", "lithology_ja": "泥質片岩"}
    plain = {"formationAge_ja": "新生代 第四紀 完新世", "group_ja": "堆積岩", "lithology_ja": "河川堆積物"}

    def fake(url, data=None, timeout=60, tries=3):
        lat = float(url.split("point=")[1].split(",")[0])
        return schist if lat < 34.08 - 0.025 else plain  # hard rock from 3 km south
    monkeypatch.setattr(lookup, "get_json", fake)
    lines, raw = lookup.rocks_japan(Site(lat=34.08, lon=134.445, country="JP"))
    assert lines[0].startswith("- `data` 周りの岩（シームレス地質図 V2）: S 3 km, SE 4 km, SW 4 km: 泥質片岩 / 変成岩 / 中生代 白亜紀。")
    assert "none within 15 km to N, NE, E, W, NW" in lines[1] and "does not say which of them the river brought" in lines[1]
    assert len(raw) == 3 + 4 + 4 + 5 * 15
