# fieldnotes

Read a field from the photos of a walk, with Meta's models, and keep what they say as plain-text records that the farmer marks right or wrong. The records stay in a folder on your own PC, and the AI you already use reads them over MCP.

- **SAM 3.1** segments each photo: crops, weeds, bare soil → cover per concept.
- **Muse Spark 1.3** (or Muse Glimmer running at home) reads the walk as one field: what is where, how it changed since the last day, and what each hypothesis about the land looks like in today's photos.
- **Muse Voice Transcribe 1.0** writes down what you say in the field; Muse Spark sorts it into work done, things seen, and verdicts on the AI's lines.
- Public land data for the farm (parcel, elevation, geology, soil; Japan in detail, world maps elsewhere) is fetched once with the source on every line.

```bash
pip install fieldnotes-farm                  # the command line, the records and the MCP server
pip install "fieldnotes-farm[app,voice]"     # plus the phone app (Flet) and the phone's voice recordings (PyAV)
```

One Meta Model API key (dev.meta.ai → API keys): set `MODEL_API_KEY`, or keep it in `~/.config/fieldnotes/model_api_key`.

```bash
fieldnotes --root ~/farm/myfield init --place "Ishii, Tokushima, Japan" --country JP --lat 34.0801 --lon 134.4454
fieldnotes --root ~/farm/myfield lookup                       # the land's public data → records/lookup.md
fieldnotes --root ~/farm/myfield observe main 2026-11-02      # the day's photos → records/main/2026-11-02.md
fieldnotes --root ~/farm/myfield mark main 2026-11-02 dominant wrong "ogi, not reed"
fieldnotes --root ~/farm/myfield propose main --cut           # where to cut first and how high
fieldnotes --root ~/farm/myfield timeline main                # what was done and what changed, by date
fieldnotes --root ~/farm/myfield mcp                          # the tools for your own AI (Claude Code, Claude Desktop, Muse Code)
```

The command and the import are `fieldnotes`; the package is `fieldnotes-farm` because `fieldnotes` on PyPI is another project.

- User manual: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/manual.md (Japanese: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/manual.ja.md)
- The record format, for other programs and AIs that read a farm folder: https://github.com/aiseed-dev/fieldnotes/blob/main/docs/records.md
- Source and issues: https://github.com/aiseed-dev/fieldnotes

Licence: AGPL-3.0-or-later.
