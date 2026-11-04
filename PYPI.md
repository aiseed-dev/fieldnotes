# fieldnotes-farm

Command line, records and MCP server for reading a farm field from the photos of a walk with Meta's models (SAM 3.1, Muse Spark 1.3, Muse Voice Transcribe 1.0). The command and the import are `fieldnotes`.

## Requirements

- Python 3.11 or later
- A Meta Model API key (dev.meta.ai → API keys), in `MODEL_API_KEY` or in `~/.config/fieldnotes/model_api_key`
- Internet access for the models, the weather and the land data; the records are written to a folder on your PC

## Install

```bash
pip install fieldnotes-farm                  # command line, records, MCP server
pip install "fieldnotes-farm[app,voice]"     # plus the phone app (Flet) and m4a/aac voice recordings (PyAV)
```

## Use

```bash
fieldnotes --root ~/farm/myfield init --place "Ishii, Tokushima, Japan" --country JP --lat 34.0801 --lon 134.4454
fieldnotes --root ~/farm/myfield lookup                       # public land data → records/lookup.md
fieldnotes --root ~/farm/myfield observe main 2026-11-02      # photos/main/2026-11-02/*.jpg → records/main/2026-11-02.md + overlays
fieldnotes --root ~/farm/myfield show main                    # the latest record
fieldnotes --root ~/farm/myfield mark main 2026-11-02 dominant wrong "ogi, not reed"
fieldnotes --root ~/farm/myfield voice main memo.m4a 2026-11-02   # what you said in the field → work / seen / marks
fieldnotes --root ~/farm/myfield propose main --cut           # where to cut first and how high → records/_proposals/
fieldnotes --root ~/farm/myfield timeline main                # every day's lines in order
fieldnotes --root ~/farm/myfield app                          # the phone app on the home network (port 8550)
fieldnotes --root ~/farm/myfield mcp                          # stdio MCP server for Claude Code, Claude Desktop, Muse Code
```

`--root` is the folder that holds `photos/` and `records/` (default: `$FIELDNOTES_ROOT`, else the current folder). Photos go in `photos/<field>/<date>/`; the app files them from the phone. Every record is Markdown with YAML front matter; the format is in `docs/records.md`.

## Links

- Manual: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/manual.md (日本語: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/manual.ja.md)
- Record format: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/records.md
- Source, issues: https://github.com/aiseed-dev/fieldnotes

Licence: AGPL-3.0-or-later.
