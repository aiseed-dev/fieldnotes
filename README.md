# fieldnotes — observing a natural-farming field together with AI

Built for the Meta Global AI Developer Hackathon (26 Oct – 4 Nov 2026), track *Indie Developer*, theme *Build for Your World*.

## Why

Farming today runs on things bought from outside: fertiliser from suppliers, and the know-how to use it from the co-op and the dealers. It is the same shape as a company that handed its IT to vendors and Microsoft. About 70 % of the world's phosphate rock reserves are in Morocco, and China has restricted phosphate fertiliser exports since 2021. As cheap, steady supply ends, depending on outside inputs becomes the weak point.

The way out is the same as in IT: buy less from outside and rebuild around the field's own strength — roots and mycorrhizal fungi cycling phosphorus. But every field has different soil and different weeds, so no single method can be handed down from above. Instead, AI reads each field — its terrain, geology, weeds and weather — and the farmer looks, works, and checks the AI against what actually happens.

The same weakness leaves land behind: about 423,000 ha of Japanese farmland was abandoned as of the 2015 census, roughly the size of Toyama Prefecture. But the force that takes land back is the soil's own strength. My field lies just south of the Median Tectonic Line in Tokushima, in the same setting as Masanobu Fukuoka's farm in Iyo, Ehime, and I am testing his natural farming here. It has had no fertiliser for four years; one plot I left uncut for a single year is now goldenrod and Amur silver grass (ogi) taller than I am, grown with nothing brought in. The soil here is rich in minerals; what is missing is the way for plants to take them up themselves — roots and mycorrhizal fungi. So the tool goes one step further on such land: it reads it and proposes where and how to cut first to bring it back into crops.

Neither the government nor the dealers teach how to cycle what is already in the soil through roots and fungi. It is like SaaS and open source: a SaaS vendor shows you how to use it, while with open source you have to learn on your own. Open source still works, because you can read the inside, what people learn is kept and shared as records, and now AI helps you read. A field can work the same way.

This project is that tool, built on my own field in Tokushima, Shikoku (no tillage, no fertiliser, no pesticides). It lets one farmer read their own field without going through a dealer or an advisor: an AI-native IT department, for a field.

Growing is not enough on its own. The biggest problem is selling. Selling, too, has been handed to the co-op and the wholesale market. Today's distribution assumes uniform shape and steady volume, and it does not carry to the buyer how a field was grown. No one supports the selling of naturally farmed produce either. So natural farming has to build its own way to sell. The records this tool keeps — the field's soil and weeds, what was done, how the crops grew, and the farmer's own checks on every reading — are first the ground for growing, and the same records become the ground for a buyer's trust.

## What it does

I photograph the same spots regularly with my phone and look at them together with the AI. The point is not a daily habit but to build up knowledge of *how to improve this field*: what I did (how I cut, what I sowed, when), how the weeds and crops changed, and whether it worked. During the hackathon I shoot daily to get enough data. Each observation:

1. **Align** each photo to the earlier ones (`field-timelapse`, SIFT + RANSAC — built before the hackathon, see below).
2. **Segment** crops, weeds, bare soil and animal tracks with **SAM 3.1** → cover % per concept per day.
3. **Describe** today against the previous days with **Muse Spark 1.3** (or **Muse Glimmer** running locally): what changed in leaf colour, weed height, soil dryness, animal signs.
4. **Verify**: I mark each AI observation right or wrong, by tapping or by voice. In the field I say what I did and saw; **Muse Voice Transcribe** writes it down in my language, and Muse Spark sorts it into work done, things seen, and verdicts on the AI's lines.
5. **Record** everything as plain Markdown that any person or model can read later. Corrections feed back into the next day's prompt.

## What was built during the hackathon

Everything in this repository: `src/fieldnotes/` (segment, describe, verify, records, report), `scripts/`, `docs/`, and the sample farm's records under `sample/` (Japanese) and `sample-en/` (the same farm read in English).

## What existed before the hackathon

* `field-timelapse` — aligns hand-held photos to a reference frame (SIFT features, RANSAC homography). Used unchanged as step 1; vendored/linked separately so the boundary is visible in the history.
* A JMA-based weather statistics site I run; this project only *reads* daily values from it.

## Meta models used

| Step | Model | How |
|---|---|---|
| Segment | `sam-3.1` | Meta Model API, one concept per request, masks → cover % (`src/fieldnotes/segment.py`) |
| Describe | `muse-spark-1.3` | Meta Model API, several days' photos in one request, JSON out (`src/fieldnotes/describe.py`) |
| Describe (local) | Muse Glimmer 30B | llama.cpp `llama-server` on a Ryzen AI Max+ 395 box in the house; same code, different `base_url`. Switch with `fieldnotes reader glimmer` or the app's 読む AI setting |
| Verify | `muse-voice-transcribe-1.0` | the farmer's recordings, language-biased to the farmer's language, with the field's plant names as keywords (`src/fieldnotes/voice.py`); Muse Spark then sorts what was said |
| Development | Muse Code | used for parts noted in commit messages |

## Running

```bash
python -m venv .venv && .venv/bin/pip install -e .
# Meta Model API key (dev.meta.ai → API keys): either set MODEL_API_KEY,
# or keep it in ~/.config/fieldnotes/model_api_key (chmod 600), which is read when the variable is unset.
```

### Your own farm

Each farm is a folder with `photos/` and `records/`. Start one with where it is; everything about the place (prompts, weather, maps) comes from the `records/site.md` this writes, never from the code, so it works for any farm in any country:

```bash
mkdir ~/myfarm && cd ~/myfarm
fieldnotes init --place "Nakuru, Kenya" --country KE --lat -0.30 --lon 36.07 --climate "highland, two rainy seasons"
```

`fieldnotes lookup` then fetches public data for the spot into `records/lookup.md`, each line with its source: elevation, bedrock (Macrostrat; in Japan also the GSJ seamless geological map), soil (ISRIC SoilGrids), and history nearby (Wikipedia articles with coordinates, OpenStreetMap castles, archaeological sites and flood memorials). `fieldnotes search 城 --save` looks for any word near the farm. Then add what you know about the land to `records/site.md` (terrain, soil, history, what works there), each line marked `data`, `record` or `hypothesis`. Hypotheses are things to check, not premises. Maps: Japan gets the GSI aerial photos (now and the 1960s–70s) and landform maps; elsewhere the OpenStreetMap standard map.

### The sample farm

`sample/` is the first farm: a natural-farming field in Tokushima, Japan, just south of the Median Tectonic Line, with its site profile, photos and records (fields `row1`, `mix1`, `uncut`). Try the commands on it with `--root sample`, or read it as an example of what a farm folder becomes. Its readings are in Japanese, the farmer's language. `sample-en/` is the same farm, same photos, read again by Muse Spark with the language set to English (`fieldnotes language en`), not translated: try `fieldnotes --root sample-en app`.

### The neighbourhood

Now and then, photograph around the fields too: the neighbours' fields and verges (herbicide, tillage), the river bank, abandoned land that sends seed, old walls. In the app choose 「近所（畑のまわり）」 when sending; `fieldnotes observe _around` reads them (no SAM), each point marked right or wrong, and the newest reading goes to every later reading of the fields. Fields and verges show land, not houses or people.

### Photos and voice, no typing

The farmer only takes photos and talks. Record with the phone's own voice recorder and send the file from the app (「声を送る」 on Send, 「声で答える」 on Read), or `fieldnotes voice uncut memo.m4a`. The recording is kept next to the day's photos, written down by Muse Voice Transcribe, and sorted by Muse Spark into:

* `work`: what the farmer did (cut, sowed, mulched, harvested);
* `seen`: what the farmer saw;
* ✓ / ✗ with the reason on the day's AI lines.

The transcript is the record's farmer note, word for word; the sorted lines can themselves be marked right or wrong, and what the farmer did and saw goes into the next reading. The app takes a file rather than the browser's microphone because browsers allow the microphone only on HTTPS or localhost.

### Daily use

Photos are filed under `photos/<field>/<date>/` by the phone app, or put there by hand. Run these inside the farm folder (or with `--root DIR`):

```bash
fieldnotes observe uncut 2026-10-28      # weather → SAM → Muse Spark → records/uncut/2026-10-28.md (+ overlays)
fieldnotes show uncut                    # the latest record
fieldnotes voice uncut memo.m4a 2026-10-28  # what you did and saw, or which lines are right or wrong, said aloud
fieldnotes mark uncut 2026-10-28 dominant right
fieldnotes mark uncut 2026-10-28 overall wrong "it is uneven, not even"
fieldnotes concept uncut goldenrod wrong "finds ogi too" --replace "yellow flowers"
fieldnotes propose uncut --seeds "crimson clover, rye"
fieldnotes propose uncut --cut           # where to cut first and how high → records/_proposals/uncut/<date>-cut.md
fieldnotes mark uncut 2026-10-29 height wrong "too high: goldenrod seeds anyway" --proposal cut
fieldnotes compare                       # rank fields by the newest record of each
fieldnotes surroundings                  # read the maps around the farm once (--force to redo)
fieldnotes reader glimmer --check        # read with Muse Glimmer at home instead of Muse Spark
fieldnotes language en                   # the AI writes in English everywhere; `auto` (default): each phone's or PC's own language
fieldnotes app --port 8550               # the phone app
```

`--root DIR` (before the subcommand) points at the folder that holds `photos/` and `records/`; the default is `$FIELDNOTES_ROOT`, else the current folder. If the `fieldnotes` command is not found, `.venv/bin/python -m fieldnotes ...` does the same (re-run `pip install -e .` to get the command).
Running `observe` again on the same day replaces the AI lines but keeps your right/wrong marks and note; a marked line whose wording changed moves under `## Earlier AI lines`.

Tests run offline: `.venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`.

### Phone app

```bash
fieldnotes --root ~/myfarm app           # http://<this machine>:8550, open it on the phone
```

Three views at the bottom: Send (photos and voice recordings into `photos/`), Read (run the observation for a field and day, look at the SAM overlays, mark each AI line ✓ or ✗ with a reason, by tap or by voice) and Nouns (the SAM noun phrases of a field, ✓ or ✗ with a replacement). The screen and the CLI are in English, or in Japanese when the language is Japanese; the language is each phone's or PC's own unless set with the 文A button or `fieldnotes language`. Everything it shows or saves is a plain-text record under `FIELDNOTES_ROOT` (default: the current directory).

### From your own AI

fieldnotes has no chat screen. You talk to the AI you already use (Claude, ChatGPT, Muse Code ...), and it calls fieldnotes over MCP; Meta's specialist models (SAM 3.1, Muse Spark or Glimmer, Muse Voice Transcribe) do the reading behind it. Photos and voice recordings still come in through the phone app.

The tools: `fields`, `read`, `observe` (takes minutes), `say` (what you tell your AI about a field, kept word for word and sorted into work, seen and right/wrong), `mark` (only what you say), `propose` (`cut` or `cover_crop`), `timeline`, `site`. Lines marked `→ farmer: right/wrong` are yours; lines without a mark are only the AI's reading, and the server tells your AI to keep the two apart.

Claude Code:

```bash
claude mcp add fieldnotes -- /path/to/fieldnotes/.venv/bin/fieldnotes --root /path/to/myfarm mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{"mcpServers": {"fieldnotes": {"command": "/path/to/fieldnotes/.venv/bin/fieldnotes",
                               "args": ["--root", "/path/to/myfarm", "mcp"]}}}
```

Muse Code (`~/.config/muse/settings.json`; see [Extending: MCP servers](https://dev.meta.ai/docs/muse-code/extending)):

```json
{"schema_version": 1,
 "mcp_servers": {"fieldnotes": {"transport": "stdio", "command": "/path/to/fieldnotes/.venv/bin/fieldnotes",
                                "args": ["--root", "/path/to/myfarm", "mcp"], "mode": "optional"}}}
```

`fieldnotes mcp --http` serves the same tools over Streamable HTTP on port 8551 (`http://<this machine>:8551/mcp`), for an AI on another machine in the house. It has no sign-in, like the phone app: keep it on the home network.

`fieldnotes timeline uncut` prints the same day-by-day view as the `timeline` tool.

## Licence

AGPL-3.0-or-later.
