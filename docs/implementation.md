# Implementation design

What to build, how the parts connect, and the work packages handed to implementers. The why lives in [story.md](story.md), and the decisions made with the farmer live in [design.md](design.md). This file is the contract. The planning session keeps it; the implementing session (Opus) owns `src/` and `tests/`.

Deadline: **2026-11-05 (Thu) 11:00 JST** (submission). Demo video recorded 11-03.

## What sells (the farmer, 2026-10-29)

> A chat alone is something nobody pays for. Offer something that solves a problem together with AI. Users keep the AI they already use and connect from there. Using a general-purpose AI for everything is inefficient.

So fieldnotes is **a back-office service that reads a field**, not a chat. Specialist models do the specialist work (SAM segments, Muse Spark or the house Glimmer reads, Muse Voice Transcribe listens); the records are plain text at the farmer's home; and the farmer, or a buyer, connects **from their own AI** through MCP. Showing twenty photos a day to a general model is slow and dear: SAM gives cover, the reading happens once, and from then on everything is text.

| Problem | Who might pay (hypothesis: say so in the README) | fieldnotes' answer | WP |
|---|---|---|---|
| Bring land that looks like abandoned farmland back into crops without buying inputs | owners of abandoned plots, new farmers, municipalities | from the weeds, geology and weather, say where to cut first and how high → the farmer cuts → the following days are recorded | 8 |
| Learn how to tend your own field without an advisor (advice, like fertiliser, is bought from outside today) | natural-farming and new farmers | daily reading → ✓/✗ → fed back into the next reading; "what I did, what changed" accumulates per field | 6, 7 |
| Make a buyer believe "no fertiliser, no pesticide" | farmers who sell direct (buyers pay for produce with a record, not for a tool) | the buyer's AI connects read-only and receives the farmer's ✓ lines as fact, AI-only lines as guesses and ✗ lines as refuted | 9b (held) |

Nine days show the start of a result, not a sale. Nothing in the README or the demo claims more.

**Scope decision (the farmer, 2026-10-29):** what matters most is selling the produce. This Meta hackathon goes as far as **production**: read the field, propose, cut, record, verify. **Selling** (a buyer's AI reading the records) goes to a Claude hackathon if the farmer can enter one; if not, it is squeezed into the end of this one (11-02). So WP9a (the farmer's own AI connecting) is in; WP9b (`export`, `--buyer`) is **held** until that is decided.

## Rules for every package

- Python ≥ 3.11, the package lives in `src/fieldnotes/`, and the venv is `.venv` (`.venv/bin/pip install -e .`).
- Match the existing code: small modules, plain dataclasses, plain-text records, docstrings that say why.
- **Records are plain text** that a person can read and edit: Markdown with YAML front matter and observation lines (`records.py`). Never add a database.
- Every AI output line can be marked by the farmer: `- key: text [conf]  → farmer: right|wrong (reason)`. Keep this line format; `records.OBS_LINE` parses it.
- Meta Model API: OpenAI-compatible at `https://api.meta.ai/v1`. The key comes from `llm.api_key()` (env `MODEL_API_KEY`, else `~/.config/fieldnotes/model_api_key`). Never print the key or log it.
- Tests run **offline**: put fakes in place of `chat` / SAM / HTTP calls (`tests/conftest.py`: `FakeModel`, the `offline` fixture). Add them under `tests/` with pytest. Spend real API credit only on one small smoke run per package, and say so in the commit.
- The screen and the CLI follow the language (`ui.py`, `llm.language()`); the AI writes in the farmer's language (`llm.in_language`). Code, comments and commit messages are in English. Commit messages end with `Co-Authored-By:` as instructed by the session.
- **Do not push.** The farmer pushes.
- Claims about the world (soil, plants, statistics) go into records only with a source that was read, never from memory (see `records/site.md`).
- Do not name a module `mcp.py`: it would shadow the `mcp` SDK package.

## Data layout

One folder per farm (`--root`, `$FIELDNOTES_ROOT`); `sample/` is the first farm, `sample-en/` the same farm read in English. The farm's place, country, climate, method and coordinates are the front matter of `records/site.md` (`site.py`, written by `fieldnotes init`); prompts get them through the `<FIELD>` and `<REGION>` tokens, the weather and the maps through `Site.load`. Nothing about a particular farm lives in the code.

```
photos/<field>/<YYYY-MM-DD>/<HHMMSS>-<name>.jpg   filed by inbox.file_photo
photos/<field>/<YYYY-MM-DD>/<HHMMSS>-voice.<ext>  the farmer's recording as the phone gave it (voice.file_voice)
photos/_around/<YYYY-MM-DD>/...                   the neighbourhood (around.py)
records/<field>/<YYYY-MM-DD>.md                   one observation (records.Record)
records/<field>/<YYYY-MM-DD>-overlay-<n>.jpg      SAM overlay per photo
records/_around/<YYYY-MM-DD>.md                   reading of the neighbourhood
records/_concepts/<field>.md                      SAM prompts per field (concepts.py)
records/_plants/<Genus_species>.md                why a weed dominates (plants.py)
records/_proposals/<field>/<date>-cover_crop.md   cover-crop proposal (propose.py)
records/_proposals/<field>/<date>-cut.md          cut proposal (WP8)
records/_export/<field>.md                        what a buyer's AI gets (WP9)
records/_compare/<date>.md                        field-to-field comparison
records/site.md, records/surroundings.md          site profile (data / record / hypothesis / refuted)
records/lookup.md, records/lookup/*.json          public data for the spot (lookup.py)
records/weather/<YYYY-MM>.json                    Open-Meteo cache
shared/sam_concepts.md                            SAM prompts shared across farms
```

Voice recordings are personal and large; whether they are committed to the public repository is the farmer's decision (default proposal: `.gitignore` them, the transcript stays in the record).

## The observation pipeline (WP1, done)

`pipeline.run_observation(field: str, day: date, root: Path = ROOT, backend: Backend | None = None) -> Record`

1. Photos: `photos/<field>/<day>/*.jpg`, sorted. If there are none, raise.
2. Weather: `weather.daily_weather(day, root/"records")` goes into `rec.weather`; a missing day must not stop the reading.
3. Previous: `records.previous_records(root/"records", field, day.isoformat(), n=3)`.
4. SAM prompts: `concepts.ensure(records, field, species_in(previous dominant lines), backend)`.
5. Segmentation: `concepts.segment_field(rec, photo_root=root, records_root=records)` fills `rec.coverage`. One overlay per photo with `segment.save_overlay`.
6. Reading: `describe.observe(rec, previous, photo_root=root, records_root=records, backend)`. This also looks up ecology for newly dominant plants, and puts the farmer's `work` / `seen` lines of the day into the prompt.
7. Prompts for next time: `concepts.ensure(...)` again, using today's dominant plants.
8. Save `records/<field>/<day>.md` and return the record.

Re-running the same field and day replaces the AI lines but **keeps the farmer's verdicts, the farmer note and the voice lines** (`pipeline.merge_rerun`; a marked line whose text changed goes under `## Earlier AI lines`).

`pipeline.mark(field, day, key, verdict, reason=None)` sets a verdict on a record line; `key#2` is the second line with that key; `work` and `seen` keys address the voice lines. Concept verdicts go through `concepts.mark`.

## CLI

`fieldnotes` console script (`[project.scripts]` in pyproject). `--root DIR` before the subcommand.

```
fieldnotes init --place P --country CC --lat LAT --lon LON   start a farm (records/site.md)
fieldnotes observe <field> [YYYY-MM-DD]          run the pipeline (default today)
fieldnotes show <field> [YYYY-MM-DD]             print the record (default the latest)
fieldnotes voice <field> <recording> [YYYY-MM-DD]  what you did and saw, or right/wrong, said aloud
fieldnotes mark <field> <date> <key> right|wrong [reason] [--proposal cut|cover_crop]   (--proposal: WP8)
fieldnotes concept <field> <noun> right|wrong [reason] [--replace NOUN]
fieldnotes propose <field> [--seeds ...]         cover-crop proposal from the latest record
fieldnotes propose <field> --cut                 where to cut first and how high (WP8)
fieldnotes timeline <field> [--since DATE]       what was done and what changed, as Markdown (WP7)
fieldnotes export <field>                        the record a buyer's AI gets (WP9)
fieldnotes mcp [--http [--port 8551]] [--buyer]  serve the tools to the farmer's own AI (WP9)
fieldnotes compare [YYYY-MM-DD]                  rank fields (latest record of each)
fieldnotes surroundings                          fetch maps + read once
fieldnotes lookup / search <words> [--save]      public data and names near the farm
fieldnotes consent [yes|no]                      may Meta train on what Spark is sent
fieldnotes reader [spark|glimmer] [--url URL] [--model NAME] [--check]
fieldnotes language [auto|ja|en|...]
fieldnotes app [--port 8550]                     the phone app
```

## Phone app (Flet web; WP3 + WP4, done)

`src/fieldnotes/app.py`, served on the house machine and opened in the phone browser. It is the way photos and voice get in from the field; reading and marking can also be done from the farmer's own AI through MCP (WP9). Views:

1. **送る / Send**: field, date, pick photos, upload → `inbox.file_photo`. 「近所」 files into `photos/_around/`. Button 「声を送る」: pick a recording (FilePicker, audio; on Android the recorder can open) → `voice.file_voice`.
2. **読む / Read**: field and date, 「読む」 runs `pipeline.run_observation` in a thread with progress; photos with SAM overlays; the record's lines with ✓ / ✗ and a reason box (`pipeline.mark`); the voice lines (`work`, `seen`) under their own heading, markable the same way; button 「声で答える」: a recording whose verdicts land on the AI lines.
3. **名詞 / Nouns**: the field's SAM concepts with ✓ / ✗ and a replacement (`concepts.mark`).

The gear (consent), the chip (reader) and 文A (language) are in the top bar. There is **no in-browser microphone**: `http://` on the LAN is not a secure context, so the phone's own recorder is used and the file is sent. Native app (WP5) and HTTPS are not planned for the hackathon. A proposal view is optional (WP7, only if time remains).

Keep it usable on a phone at 375 px wide: large tap targets, no horizontal scroll.

## Consent to training (2026-10-28)

Muse Spark has a cheaper contributor model (`muse-spark-1.3-contributor`), and Meta may train on what is sent to it. The app asks the farmer on first launch, before anything is sent, and the gear changes the answer later. The CLI does the same with `fieldnotes consent [yes|no]`. The answer is kept in `~/.config/fieldnotes/settings.json` (`llm.training_consent`). `Backend.spark()` uses the contributor model only after a yes.

## Which model reads (2026-10-28)

SAM always runs on api.meta.ai. The reading (describe, plants, propose, surroundings, voice sorting) goes to the model the farmer picks: Muse Spark on api.meta.ai (default), or Muse Glimmer on the house machine, so photos need not leave the house. Setting `reader` in `settings.json` with `glimmer_url` and `glimmer_model` (defaults `http://192.168.100.6:11434/v1`, `muse-glimmer-30B`). `Backend.default()` follows it. Glimmer runs as llama.cpp `llama-server` (ROCm, `scripts/setup-glimmer-server.sh`). First real reading 2026-10-28: 267 s, sensible, but in English despite the language rule; **check once more after 77c491d** (WP6).

## Voice (WP2 + WP4, done 2026-10-29, commit 6ac6d09)

The farmer does not type. `voice.py`:

1. The recording the phone gives (m4a, 3gp, ogg, webm, WAV ...) is kept as it is at `photos/<field>/<date>/<HHMMSS>-voice.<ext>`.
2. PyAV (`av`) decodes it to 24 kHz mono 16-bit WAV (no ffmpeg binary). `voice.transcribe(data, keywords, lang)` posts to `POST https://api.meta.ai/v1/asr/transcribe` (multipart: `request` JSON + `audio`): `model muse-voice-transcribe-1.0`, `audioEncoding WAV`, `mode PUSH_TO_TALK`, `keywords` from `voice.vocabulary(field, records)` (the field's plant names, its SAM targets, the farm words of the language from `ui.py`), `languageBias` from `llm.language()` (`zh` → "Mandarin Chinese"; unsupported → none).
3. Muse Spark (or Glimmer) sorts the transcript (`voice.sort_speech`) into `work` (what the farmer did), `seen` (what they saw) and `verdict` (right / wrong on one of today's AI lines, with the reason).
4. `voice.apply` puts them in the record: the transcript under `## Farmer note (muse-voice-transcribe-1.0, <lang>)` as `HH:MM text (file)`; `work:` / `seen:` lines under `## From the farmer's voice (<model>)`, markable (`pipeline.mark work#2 ...`); verdicts straight onto the AI lines. A verdict on a line that does not exist is kept as `seen`.
5. These lines survive a re-run and, unless marked wrong, go into the next describe prompt (`describe._voice_part`).

Verified: 60 offline tests; a real `/v1/asr/transcribe` call returned 200 (test tone, empty transcript); a real Spark sort of a typed Japanese sentence. **Not yet verified: a real spoken Japanese recording** (the farmer records one in Niihama on 10-29).

## WP8: the cut proposal (where to cut first, how high)

The climax of story.md ("刈り方の提案 [F]"): the `uncut` plot has had no fertiliser for four years and was left uncut for one; it now looks like abandoned farmland (ogi and goldenrod above head height). The tool proposes **one place and one height to cut first**, with the reason; the farmer cuts (or rejects with a reason), and the following days' photos show what comes back.

**Critical path**: proposal and cut on 10-30 / 10-31, so that regrowth photos exist before the video on 11-03. Build it on 10-29.

Reuse `propose.py` as it is shaped: `Proposal` already has `kind` and `path_for(kind)`.

- `propose.KIND_CUT = "cut"`. `propose_cut(latest: Record, date: str, records_root: Path, backend: Backend) -> Proposal`, saved at `records/_proposals/<field>/<date>-cut.md` with `kind: cut` in the front matter. `Proposal.to_markdown` must take its heading from the kind ("Cut proposal (<model>)"), and `earlier_proposals` must take the kind, so wrong-marked points of earlier cut proposals are not repeated.
- Context, the same as the cover-crop prompt (`build_messages`): the latest record (overall, dominant, barometers), plant notes for the dominant species, `site_background` (terrain, geology, moisture, history, the farmer's own knowledge), the date, earlier proposals marked wrong. Plus the **cover and its source**: when SAM found the species (coverage > 0), give the SAM shares; when it did not (as in `sample/records/uncut/2026-10-28.md`: silvergrass, goldenrod, leaf and bare soil all 0.0, only "flower cluster" 3.1 %), say in the prompt that the shares come from the AI's own reading of the photos (the `dominant` line, ~60 % / ~30 %), and make the proposal say which source it rests on (a `basis` line).
- Its own `CUT_SYSTEM`, in the manner of `SYSTEM`: natural farming, so no tillage and no pulling of roots; cut and lay as mulch (刈り敷き); the aim is to bring the plot back into crops step by step, not to clear it; mind the season in `<REGION>` at this date (goldenrod in flower or seed: cut before seed set; ogi tall and dry); mind terrain and moisture from the site background; the farmer's knowledge in the site background overrides; **one place and one height**, not a menu; low confidence rather than a guess. JSON only.
- Lines (`parse_cut`), each with `[conf]`, each markable:
  - `summary`: one sentence: where first, how high, why.
  - `basis`: what the proposal rests on: "SAM cover: ..." or "AI estimate from the photos: ...", plus the site facts used.
  - `where`: the part of the plot to cut first, described so the farmer can find it in the photo (edge, strip width, direction).
  - `height`: the cutting height and why (root crowns and mulch kept, regrowth expected).
  - `leave`: what not to cut and why (a stand of ogi as windbreak or mulch source, the roots and their fungi).
  - `method`: cut and lay, tool, order.
  - `watch`: what the next days' photos should show if it was right (what regrows first, bare soil, seedlings) and what would show it was wrong.
  - `caution`: optional.
- Marking: `propose.mark(records_root, field, date, kind, key, verdict, reason=None) -> Observation`; CLI `fieldnotes mark <field> <date> <key> right|wrong [reason] --proposal cut|cover_crop`. The farmer's ✗ with a reason is the record of a rejected proposal.
- CLI: `fieldnotes propose <field> --cut` (prints the proposal; `--seeds` stays for the cover crop). `fieldnotes show` is unchanged.
- Tests (offline): add a `cut` kind to `FakeModel` (match `propose.CUT_SYSTEM`), check path and front matter, `parse_cut`, the basis sentence when SAM shares are 0 vs. when they are not, the wrong-marked earlier cut point excluded, and `propose.mark` on a proposal line. One real run on `sample` `uncut` (the 10-28 record, or 10-29's if the photos arrive); commit the proposal file with the run noted in the commit.
- WP6 companion: retry SAM nouns for `uncut` on the next photos (`fieldnotes concept uncut goldenrod wrong "no match" --replace "yellow flowers"`, "tall grass", ...), so the basis can become SAM later.
- Done: tests pass, `sample/records/_proposals/uncut/<date>-cut.md` exists from a real run, README "Daily use" gets the two lines, committed. Then the farmer cuts.

## WP9: connect from your own AI (MCP server)

The farmer and the buyer use the AI they already have. fieldnotes serves its functions as MCP tools; the Flet app stays the way photos and voice get in. **9a** (the farmer's tools, `say`, the README section) is this hackathon's work. **9b** (`export`, `--buyer`) is the selling side and is held: it goes to a Claude hackathon if there is one, else into 11-02.

- Dependency: `mcp` (the Python MCP SDK, `FastMCP`) in `pyproject.toml`. Module `src/fieldnotes/mcp_server.py` (not `mcp.py`). CLI `fieldnotes mcp [--http [--port 8551]] [--buyer]`: stdio by default; `--http` serves Streamable HTTP on the LAN; `--buyer` registers the read-only tools only. `--root` applies as everywhere.
- Tools (each a thin call of an existing function; return Markdown, since the records already are):
  - `fields()` → each field with its record dates and the farm's place (`pipeline.fields_with_records`, `pipeline.record_dates`, `Site.load`).
  - `read(field, day=None)` → the record (`Record.load` / `pipeline.latest_record`).
  - `observe(field, day=None)` → runs `pipeline.run_observation` and returns the record (takes minutes; say so in the tool description).
  - `say(field, day, text)` → the farmer's words, already heard by their own AI: `voice.sort_speech` + `voice.apply` without transcription (factor `file_voice` so the text path can be reused). Returns what changed.
  - `mark(field, day, key, verdict, reason=None)` → `pipeline.mark`; `proposal` argument routes to `propose.mark`.
  - `propose(field, kind="cut", seeds=None)` → WP8 / cover crop; returns the proposal.
  - `timeline(field, since=None)` → WP7.
  - `export(field)` → below (9b, held).
  - `site()` → `records/site.md` and `records/lookup.md`.
  - `--buyer` mode: `fields`, `site`, `timeline`, `export` only (9b, held).
- 9b, held — `export(field)` (`export.py`, also `fieldnotes export <field>`, saved at `records/_export/<field>.md`): what a buyer's AI gets, with the farmer's knowledge, the AI's guesses and public data kept apart (evidence rules):
  1. Where: place and country from `site.md` front matter; the `data` lines of `site.md` and `lookup.md` with their sources. `hypothesis` lines are left out.
  2. How it is farmed: the method from `site.md`; the `work` lines from the records, dated.
  3. What the farmer confirmed: AI lines with `farmer: right`, dated, with the model that wrote them.
  4. What the AI read and the farmer has not checked: unmarked lines, under a heading that says so.
  5. What the farmer refuted: `farmer: wrong` lines with the reason.
  6. Photos and cover per date (paths, SAM coverage), weather in one line per date.
  7. Sources.
- Tests (offline): the tool functions on the `root` fixture; one test that lists the tools through an in-memory client session of the SDK (and in `--buyer` mode once 9b exists); for 9b, `export` on a record with right / wrong / unmarked lines and a `hypothesis` line in site.md that must not appear as fact.
- Real check: `claude mcp add fieldnotes -- <abs>/.venv/bin/fieldnotes --root <abs>/sample mcp`, then ask Claude Code to list the fields and read `uncut` (for 9b later: a `--buyer` run that asks "was fertiliser used?"). README section "From your own AI" with the config for Claude Desktop (`claude_desktop_config.json`) and Claude Code; check on dev.meta.ai whether Muse Code can take an MCP server and, if so, add its config (the farmer asked).
- Done: tests pass, the real check with Claude Code done once, README section, committed.

## WP7: the demo — timeline, README, script

- `timeline.py`: `timeline(field, records_root, photo_root, since=None) -> str`, Markdown, one block per date (oldest first): the photos (relative paths), weather in one line, the `overall` line with its verdict, the `work` and `seen` lines, the count of ✓ / ✗, any proposal of that day (its `summary` line and verdict). CLI `fieldnotes timeline <field> [--since DATE]`. The MCP `timeline` tool calls the same function. An app view only if time remains.
- README (the planning session writes the structure, the implementing session adds the command lines of WP8 / WP9): who it is for and which problem (the table above, marked as hypotheses), "from your own AI", which specialist model does what, the names of the actual modules (`voice.py`, `propose.py`, `timeline.py`, `export.py`, `mcp_server.py`), Muse Code's use only where a commit says `Written with Muse Code`.
- `docs/demo.md` (planning session): the three-minute script, in this order: the problem (a plot that looks like abandoned land; no advisor; selling) → from the AI you already use, connect to fieldnotes → "read this plot" (SAM + Spark) → "where do I cut first?" (WP8) → the cut → answering by voice → the timeline a few days later → (only if 9b is built) the buyer's AI connects read-only: "really no fertiliser?" → the ✓ lines with their sources → close (specialist models do the work, you keep your own AI, the records stay at home). No chat screen. Respect story.md's cautions: never say "depletion", say "a plot that came to look like abandoned land", never say "restored" after nine days.

## Work packages

| WP | What | Depends on | Who | State |
|---|---|---|---|---|
| 1 | pipeline, overlays, CLI, pytest with offline fakes | – | Sonnet session | done |
| 2 | `voice.py`: Muse Voice Transcribe + Spark sorting | – | Opus (Muse Code was not running) | done, 6ac6d09 |
| 3 | app views 読む, 名詞 | 1 | Sonnet session | done |
| 4 | voice in the app (声を送る / 声で答える) | 2, 3 | Opus | done, 6ac6d09 |
| 5 | native capture app | – | – | **dropped** |
| 6 | real runs on the farmer's photos daily; SAM nouns and prompts tuned; second farm (Niihama) from `init`; Glimmer language checked | 1 | Opus + farmer | daily to 11-02 |
| 7 | timeline, README, demo script | 1, 6, 8, 9 | Opus (timeline) / planning session (README, demo.md) | 11-01 – 11-02 |
| 8 | cut proposal | 1 | Opus | done, cf490d7 (real run: `sample/records/_proposals/uncut/2026-10-29-cut.md`; the farmer's ✓/✗ and the cut follow on 10-30) |
| 9a | MCP server for the farmer's own AI: `fields`, `read`, `observe`, `say`, `mark`, `propose`, `timeline`, `site`; README "From your own AI" | 1, 2, 8 | Opus | started 10-29 |
| 9b | `export`, `--buyer` (selling) | 9a | Opus | **held**: Claude hackathon, else 11-02 |
| – | Muse Code review (docs/muse-code.md Task 2) | – | farmer runs `muse` | by 11-02 |

Done for each package means: tests pass offline, one short real run when the package calls the API, the README section updated, and the work committed on main (or a branch) with a summary of what was and was not verified.

## Schedule to the deadline

| Day | Implementation (Opus) | Farmer |
|---|---|---|
| 10-29 Thu | WP8 cut proposal, tests, one real run on `uncut` | Niihama farm visit: photos, voice notes (the first real Japanese recording), three questions (who advises you, how do you sell, what would you pay to have solved). Evening on the LAN: `init` the second farm, send, `observe`, `voice` |
| 10-30 Fri | WP9 MCP server | morning: `fieldnotes propose uncut --cut` on the new photos; cut, or reject with a reason; daily photos |
| 10-31 Sat | WP9a: `say`, README "From your own AI", real check with Claude Code | cut if not yet; photos of the cut plot |
| 11-01 Sun | WP7 timeline | photos; planning session: `docs/demo.md`, README structure |
| 11-02 Mon | README final, code tidy, nova's fork checked for parts to merge; WP9b only if selling stays in this hackathon | Muse Code Task 2 review; photos |
| 11-03 Tue | – | video: field footage, screen recording from the own AI, edit |
| 11-04 Wed | buffer | submission form (team members added here; public repo pushed) |
| 11-05 Thu 11:00 JST | **deadline** | |
