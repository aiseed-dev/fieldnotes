# fieldnotes user manual

Written from the code as of 2026-11-03 (`fieldnotes --help` and every subcommand's help, `src/fieldnotes/app.py`). The README gives the whole picture; [records.md](records.md) says what every file and line in a farm folder means. This page says only how to use it day by day. Japanese version: [manual.ja.md](manual.ja.md).

## 1. What it is

fieldnotes reads a farmer's field together with AI and keeps the reading as plain-text records at home. The farmer takes photos, marks lines, and can talk instead of typing. It is for any farm, whatever way it is worked; the app has no method of its own.

- **SAM 3.1** segments crops, weeds and bare soil in each photo and gives their cover (%).
- **Muse Spark** reads the photos against the previous days and the public data about the land, and writes lines.
- **Muse Voice Transcribe** writes down what the farmer said in the field; Spark sorts it into what was done, what was seen, and ✓ / ✗ on the AI's lines. (Built; not yet used on a real recording as of 2026-11-05.)

Every line the AI writes can be marked `right` (✓) or `wrong` (✗) with a reason, and the corrections feed the next reading. There is no chat screen: connect from the AI you already use (Claude, ChatGPT, Muse Code ...) over MCP, or use the command line or the phone app. The records are Markdown that any person or model can read.

## 2. Setting up

### 2.1 Install

From the repository as it is (the farmer's PC today):

```bash
cd /home/dev/dev/fieldnotes
.venv/bin/fieldnotes --help
```

A fresh install:

```bash
python -m venv .venv && .venv/bin/pip install -e ".[all]"
```

`[all]` adds the phone app (Flet) and the decoding of the phone's voice recordings (PyAV). If the `fieldnotes` command is not found, `.venv/bin/python -m fieldnotes ...` does the same.

`pip install fieldnotes-farm` installs it from PyPI (since 2026-11-04); the extras are `[app,voice]`.

### 2.2 The Meta key

Put the Model API key from dev.meta.ai in one of two places:

- the environment variable `MODEL_API_KEY`;
- the file `~/.config/fieldnotes/model_api_key` (`fieldnotes` is a **folder**, `model_api_key` the **file** inside it; permissions 600).

```bash
mkdir -p ~/.config/fieldnotes && chmod 700 ~/.config/fieldnotes
# write the key to ~/.config/fieldnotes/model_api_key and chmod 600 it
```

The key is read at every call, so nothing needs restarting after you place it. When it is missing, the error reads `no Meta Model API key: set MODEL_API_KEY or write it to ...`.

### 2.3 First settings (each prints its current value when given no argument)

| Command | Meaning |
|---|---|
| `fieldnotes consent yes` / `no` | whether Meta may train on what is sent to Muse Spark. The app asks the same thing in a dialog on first start (the gear icon changes it later) |
| `fieldnotes language ja` / `en` / `auto` | the language the AI writes in. `auto` (default) is each phone's or PC's own |
| `fieldnotes reader spark` / `glimmer` | the model that reads the fields. `glimmer` is a llama.cpp server in the house (default `http://192.168.100.6:11434/v1`; `--url` and `--model` change it, `--check` asks whether it answers). Day to day, and for the video: `spark` |

## 3. Starting a farm

One farm = one folder with `photos/` and `records/`. Run the commands inside that folder, or give `--root DIR` **before** the subcommand. The default is `$FIELDNOTES_ROOT`, else the current folder.

```bash
mkdir ~/farm/myfarm && cd ~/farm/myfarm
fieldnotes init --place "Niihama, Ehime, Japan" --country JP --lat 33.912172 --lon 133.264208 \
  --climate "warm temperate, humid" --method "former paddy; no tillage, no fertiliser and cutting are not premises; no pesticide"
```

- `--method` is how the farm is worked, in your own words. It goes into every prompt. The app has no method of its own: leave it out and `site.md` says `method: not recorded yet`, and so do the prompts. Edit the `method:` line in `records/site.md` whenever you want.
- A second `init` does not overwrite an existing `site.md` (it says so and stops).

Then fetch the public data about the spot:

```bash
fieldnotes lookup                 # elevation, bedrock, soil, active faults, hazard zones, the farmland parcel, the geological map sheet, places nearby → records/lookup.md
fieldnotes search castle --save   # look for a word near the farm (Wikipedia, OpenStreetMap) and add it to lookup.md
fieldnotes surroundings           # read the map tiles around the farm once (--force to redo)
```

What you know goes into `records/site.md` with `note`; every line carries its kind.

```bash
fieldnotes note "the pole goes in about 20 cm and takes force to pull out"       # your own words → a `record` line
fieldnotes note --source "Ishii town history (1991) p.833" --section history "..." # what a document says → a `data` line with its source
fieldnotes note --page page.jpg                                                   # a photographed page: the reading model copies out what concerns the farm
```

`--section` is `terrain`, `geology`, `history` or `works`; `--date` is when you said it (default today). `hypothesis` lines are things to check, never premises.

## 4. Daily use

### 4.1 Walk the field and shoot

- Walk the same route each day with the phone's **location on** and take 20–50 photos. One reading takes up to 50 photos; a longer walk is read in parts and then combined.
- The photos are filed in capture order under `photos/<field>/<date>/`, with `index.json` holding each photo's time, GPS point and facing.
- In the reading each photo is called "3 of 42, 10:21, NW corner, facing W". The position words (NW corner, middle, S edge ...) are relative to the **farmland parcel** (筆ポリゴン) when it holds at least half of the photo points. Otherwise the frame is the area the walk covered, and each photo also says `in the parcel` or `outside the parcel, 35 m S` (distance and direction from the parcel's nearest edge). In that case "S edge" is the south end of the walk, not of the field, and the model is told to write "outside the parcel" with the distance into any zone seen only in such photos.
- Now and then photograph around the fields too (the neighbours' fields, verges, the river bank, abandoned land). In the app choose "Neighbourhood (around the fields)"; on the command line the field is named `_around`, and `fieldnotes observe _around` reads it (no SAM). Land, not houses or people.

### 4.2 The phone app (the main way to use fieldnotes)

Start it on the PC and open it in the phone's browser (home network only; there is no sign-in).

```bash
fieldnotes --root ~/farm/myfarm app --port 8550     # on the phone: http://<the PC's address>:8550
```

On start the PC's terminal prints the address and its QR code: point the phone's camera at it. The screen is dark (easier to read outdoors). For the video, start it with `FIELDNOTES_DEMO=1` in the environment: a camera button at the top right saves the screen as it is as a 1280×720 PNG under `<farm>/video/frames/` (open the app in a 1280×720 browser window for a full frame).

Four views at the bottom:

| View | What it does |
|---|---|
| **Send** | pick the field and the day (from a calendar), "Take or choose, and send" for photos (a new field name can be made here). "Send your voice (what you did and saw)" sends a file from the phone's recorder |
| **Read** | pick the field and the day, "Read" runs the observation (minutes). Look at the photos and the SAM overlays, mark each AI line ✓ or ✗ (with a reason). "Answer by voice (✓ ✗ and why)" does the marking by voice. Under the title: which model will read next and in which language. Every reading is headed by its model and date; what the screen cannot show is said ("No reading yet", "SAM found nothing for these prompts", "Voice not transcribed") |
| **Land** | `site.md` and `lookup.md` line by line: `data` with its source (addresses open), `record` in the farmer's words, `hypothesis` with how to check it and what each day's photos said; the hypotheses-by-day table; the fertiliser and soil-carbon baseline is marked "not yet". At the bottom, the command line's work: start the land (`init`) when there is no `site.md`, add what you know (`note`), and per field the timeline as text, the expectations (`expect`) and the proposals (`propose`, a cut or cover crops); the AI's results open headed by the model and the date |
| **Nouns** | the noun phrases SAM is asked to find ("yellow flower clusters" ...) and what each found last time; ✓ / ✗ and a replacement noun |

Top right: the 文A button sets the screen's and the AI's language, the chip button picks the reading AI, the gear changes the training consent. Browsers allow the microphone only on HTTPS or localhost, so record with the phone's own recorder and send the file (m4a, 3gp, ogg, webm or WAV).

In a desktop browser pane the Japanese text may show as boxes; that is the renderer's font, not the app. The phone shows it properly.

### 4.3 The same from the command line

```bash
fieldnotes observe uncut 2026-11-03       # weather → SAM → Muse Spark → records/uncut/2026-11-03.md (+ overlay images); without a date: today
fieldnotes show uncut                     # the latest record (or the given day's)
fieldnotes voice uncut memo.m4a 2026-11-03   # transcribe the recording and sort it into work / seen / ✓✗ in the record
fieldnotes mark uncut 2026-11-03 dominant right
fieldnotes mark uncut 2026-11-03 overall wrong "it is uneven, not even"
fieldnotes mark uncut 2026-11-03 zone#2 wrong "that is the neighbour's paddy"   # key#2, key#3 when a key appears more than once
fieldnotes concept uncut goldenrod wrong "finds ogi too" --replace "yellow flower clusters"
fieldnotes timeline uncut                 # day by day, plus the tables "species coming up × day" and "hypotheses × day" (--since DATE)
```

- Running `observe` again on the same day rewrites the AI lines but keeps your ✓ / ✗ and note. A marked line whose wording changed moves under `## Earlier AI lines`.
- The AI's line keys: `overall`, `dominant`, `crops`, `acidity`, `fertility`, `dryness`, `zone`, `emerging`, `leaf_colour`, `weed_height`, `soil`, `animal`, `other`. From the farmer's voice: `work`, `seen`.

### 4.4 Proposals and checking hypotheses

```bash
fieldnotes propose uncut --cut                          # where to cut first and how high → records/_proposals/uncut/<date>-cut.md
fieldnotes propose uncut --seeds "crimson clover, rye"  # a cover-crop mix from the seeds on hand
fieldnotes mark uncut 2026-11-03 height wrong "too high" --proposal cut

fieldnotes expect uncut                                 # before any photo: what photos would show for each hypothesis in site.md → records/_checks/uncut/expect.md
fieldnotes mark uncut 2026-11-03 h3 wrong "photos cannot show this" --proposal expect
fieldnotes compare                                      # the fields side by side on the weed barometers, from each one's newest record → records/_compare/<date>.md
```

Once `expect` has been written, every later `observe` adds a `## Checks` section to the record (`agrees` / `disagrees` / `cannot tell` per hypothesis). Before sowing, `cannot tell` is often the right answer. The table at the end of `timeline` shows the answers day by day.

## 5. From your own AI (MCP)

Photos and voice still come in through the app; the reading and the marking you ask your usual AI for.

```bash
# Claude Code
claude mcp add fieldnotes -- /home/dev/dev/fieldnotes/.venv/bin/fieldnotes --root /home/dev/farm/rokuse mcp
```

Claude Desktop (`claude_desktop_config.json`):

```json
{"mcpServers": {"fieldnotes": {"command": "/home/dev/dev/fieldnotes/.venv/bin/fieldnotes",
                               "args": ["--root", "/home/dev/farm/rokuse", "mcp"]}}}
```

Muse Code (`~/.config/muse/settings.json`):

```json
{"schema_version": 1,
 "mcp_servers": {"fieldnotes": {"transport": "stdio", "command": "/home/dev/dev/fieldnotes/.venv/bin/fieldnotes",
                                "args": ["--root", "/home/dev/farm/rokuse", "mcp"], "mode": "optional"}}}
```

The tools: `fields`, `read`, `observe` (takes minutes), `say` (what you tell your AI about a field, kept word for word and sorted into work, seen and ✓ / ✗), `mark` (only what you say), `propose` (`cut` or `cover_crop`), `timeline`, `site`, `note`. The server tells your AI that only lines with `→ farmer: right/wrong` are yours; a line without a mark is the AI's reading alone.

For an AI on another machine: `fieldnotes mcp --http` (port 8551, `http://<the PC>:8551/mcp`). No sign-in, so keep it on the home network.

## 6. Reading a record

Every line has the same shape:

```
- <key>: <text> [0.85]  → farmer: right | wrong (reason)
```

`[0.85]` is the AI's confidence (0 to 1). `→ farmer:` is added later by `mark`; the AI never writes it. A line without it has not been judged.

Lines in `records/site.md` begin with their kind: `data` (public data or a document, with its source), `record` (what the farmer did or saw), `hypothesis` (a reading not yet checked), `supported` / `refuted` (checked). What the AI read from photos never goes into `site.md`: if it did, the next reading would repeat it as fact.

The main files (all of them in [records.md](records.md)):

```
photos/<field>/<date>/                photos, recordings, index.json
records/<field>/<date>.md             one day's observation (AI lines, Checks, the farmer's voice, ✓ / ✗)
records/<field>/<date>-overlay-<n>.jpg what SAM found, drawn on photo n
records/site.md                       what is known or believed about the land
records/lookup.md                     what lookup found, with sources
records/_proposals/<field>/           cut and cover-crop proposals
records/_checks/<field>/expect.md     what the photos would show for each hypothesis
records/_concepts/<field>.md          the nouns SAM is asked for
records/_plants/<Genus_species>.md    why a dominant weed dominates (the AI's reading)
```

`sample/` is a real farm folder in this form (Tokushima, in Japanese); `sample-en/` is the same photos read again in English.

## 7. When something goes wrong

| Symptom | What to do |
|---|---|
| `no Meta Model API key` | put it in one of the two places of 2.2; check the folder and file names |
| `fieldnotes: command not found` | use the full path `.venv/bin/fieldnotes`, or `.venv/bin/pip install -e .` |
| `fieldnotes app` or an m4a recording asks for an extra | `.venv/bin/pip install -e ".[app,voice]"` |
| the positions do not match the field ("S edge" is the terrace next door) | see 4.1: when fewer than half the photos lie in the parcel, the walk is the frame. Look for `in the parcel` / `outside the parcel, … m` in the labels; walk from the middle of the parcel |
| SAM's cover is near zero | tall dense stands, stubble, black mulch and water are often missed by the current nouns. Try another phrase in the Nouns view or with `concept --replace`. The proposal's `basis` line says which numbers are SAM's and which are the AI's own reading |
| photos from another disk fail with `Invalid cross-device link` | fixed in the code of 2026-11-03; on an older version copy them to the same disk first |
| you want to read the same day again | run `observe` again; ✓ / ✗ and the note stay |
| the AI repeats its own earlier reading as fact | check that no AI reading got into `site.md`; the notes under `_plants/` are the AI's |
| the phone cannot open the app | same Wi-Fi as the PC, port 8550 open; the address is `http://<the PC's IP>:8550` |

## 8. Terms

- **field**: a named part of the farm (`uncut`, `mix1`, `row1`, `main` ...); the folder's name.
- **筆ポリゴン (farmland parcel)**: 農林水産省's farmland parcel data; reference information for position and shape, showing neither boundaries nor rights.
- **zone**: a part of the field that differs from the rest. **emerging**: a sown or planted species coming up (not a self-sown or mature plant).
- **Checks / h1, h2 ...**: the hypotheses of `site.md` by their order, and which way the day's photos pointed for each.
