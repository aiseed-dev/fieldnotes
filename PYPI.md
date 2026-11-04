# fieldnotes-farm

Command line, records and MCP server for reading a farm field from the photos of a walk with AI. The command and the import are `fieldnotes`.

What does the work:

- Segmenting each photo (crops, weeds, bare soil → cover): SAM 3.1 on the Meta Model API.
- Reading the walk as one field, checking hypotheses, sorting what you said: any OpenAI-compatible chat model. Default Muse Spark on the Meta Model API; or a server in your house (llama.cpp, Ollama, …) with `fieldnotes reader glimmer --url http://<host>/v1 --model <name>`.
- Writing down your voice recordings: Meta's transcription API.
- Using the records: any MCP client (Claude Code, Claude Desktop, Muse Code, …) through `fieldnotes mcp`.

## Requirements

- Python 3.11 or later
- A Meta Model API key (dev.meta.ai → API keys) for SAM and the voice, in `MODEL_API_KEY` or in `~/.config/fieldnotes/model_api_key`
- Internet access for the models (unless the reader is at home), the weather and the land data; the records are written to a folder on your PC

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
fieldnotes --root ~/farm/myfield reader glimmer --url http://192.168.1.10:11434/v1 --model my-model --check
fieldnotes --root ~/farm/myfield app                          # the phone app on the home network (port 8550)
fieldnotes --root ~/farm/myfield mcp                          # stdio MCP server; --http for an AI on another machine
```

`--root` is the folder that holds `photos/` and `records/` (default: `$FIELDNOTES_ROOT`, else the current folder). Photos go in `photos/<field>/<date>/`; the app files them from the phone. Every record is Markdown with YAML front matter; the format is in `docs/records.md`, so any program or AI can read a farm folder.

## Links

- Manual: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/manual.md (日本語: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/manual.ja.md)
- Record format: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/records.md
- Source, issues: https://github.com/aiseed-dev/fieldnotes

Licence: AGPL-3.0-or-later.
