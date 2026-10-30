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

### How it is paid for (the farmer, 2026-10-29, on the train)

> To be used it has to be free. The question is how to cover the running costs under that. And something that sells still has to be made.

The line runs where a server is needed.

- **Free, to be used:** the software in the public repository, run at the farmer's home, records as plain text there, the Meta API key the farmer's own (they pay Meta for what they use; the house Glimmer costs nothing per call). We run no server, so there is no running cost to cover. The design makes the free layer free.
- **Paid, to cover the running costs (hypotheses, written as such in the README):**
  1. **The buyer's window:** a public, read-only, HTTPS endpoint where a buyer's AI reads one farm's records (`--buyer`). A domain and a host; a small monthly fee per farm; the reason to pay is selling produce with a record. This is the second half of WP9b and needs hosting; a box at home sits behind NAT and cannot serve it.
  2. **A box with support:** a PC with fieldnotes and Claude set up, rented with support. Support is the product (an answer for the farmer who has no advisor); the PC is how it is delivered without touching the farmer's own computer. Records stay in the farmer's house and leave with them when they stop. The phone stays the camera, over the LAN as now; Claude Desktop connects to `fieldnotes mcp` inside the same box, so no server, HTTPS or domain is needed. **Decision (the farmer, 2026-10-29): Claude on a Team plan.** The renter's organisation is the admin; each farm is one named seat; the seat is passed through at cost, the API at cost. Checked 2026-10-29 on claude.com/pricing and the Team plan help article: Standard seat $25 per member per month billed monthly ($20 annual), minimum two members, up to 150, "each seat is for one named individual", "admin controls for remote and local connectors", the desktop app and desktop extensions listed for Team, no training on content by default; US prices, may differ by region. Hardware: SAM and Spark through the API need only a cheap mini PC; running Glimmer in the box needs a large machine and is slow (212 s per photo on `halo`). The limit of this business is support time, which grows with the number of farms and competes with time in the field.
  3. **A cut report:** the WP8 proposal as a one-off paid report to owners of abandoned plots and municipalities.
- **What sells, for the farmer themselves:** produce with a record. The buyer's window is what makes the record believable.

How members get in (checked 2026-10-29 on support.claude.com): the admin invites by email or by an invite link; each person signs up or logs in with their **own** Claude login (one named seat each; nobody can be entered by someone else, and the consumer terms of 2025-10-08 forbid sharing an account or making it available to anyone else; 18 or older). The organisation's creator needs a business e-mail, but public domains such as gmail.com can be added as allowed domains for the other members, so a farmer with a Gmail address can be invited. A pending invitation takes a seat at once; a removed member loses access at once but the seat count stays until the admin lowers it. For a class (AI 教室): the teacher demonstrates on their own account, or each participant brings their own free account; a Team seat is only for someone who will keep using it.

Nothing here changes what is built by 11-05. Checks that wait until after the deadline: Anthropic's commercial terms (effective 2025-06-17) let a Customer offer the Services to its own "Users" (A.1) but forbid reselling them "except as expressly approved by Anthropic" (D.4(a)), so ask Anthropic before the first box goes out; whether a custom desktop extension (`fieldnotes mcp`, stdio) uploaded by the Team admin reaches every member's Claude Desktop (the help article says owners manage which extensions members can use and can upload custom ones); Team prices in Japan.

**Scope decision (the farmer, 2026-10-29):** what matters most is selling the produce. This Meta hackathon goes as far as **production**: read the field, propose, cut, record, verify. **Selling** (a buyer's AI reading the records) goes to a Claude hackathon if the farmer can enter one; if not, it is squeezed into the end of this one (11-02). So WP9a (the farmer's own AI connecting) is in; WP9b (`export`, `--buyer`) is **held** until that is decided (the farmer decides on 10-30).

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

SAM always runs on api.meta.ai. The reading (describe, plants, propose, surroundings, voice sorting) goes to the model the farmer picks: Muse Spark on api.meta.ai (default), or Muse Glimmer on the house machine, so photos need not leave the house. Setting `reader` in `settings.json` with `glimmer_url` and `glimmer_model` (defaults `http://192.168.100.6:11434/v1`, `muse-glimmer-30B`). `Backend.default()` follows it. Glimmer runs as llama.cpp `llama-server` (ROCm, `scripts/setup-glimmer-server.sh`). First real reading 2026-10-28: 267 s, sensible, but in English despite the language rule. Checked again 2026-10-29 on a scratch copy of `sample` (`uncut` 10-28, one photo): 212 s in all (SAM 3 s, Glimmer about 209 s); **still English** in every free-text line, only the plant names came back in Japanese, so the `in_language` rule at the end of the system prompt is not enough for Glimmer (Spark follows it). The re-run kept the farmer's marks (moved under "Earlier AI lines" because the wording changed), the voice lines and the note, and Glimmer used the voice lines.

Open item (WP6, scheduled 11-02 unless the farmer wants it earlier; the demo uses Spark): put the language rule at the **start** of the system prompt and repeat it at the end of the user message; one real Glimmer run to confirm; if still English, say so in the README under Glimmer rather than adding a second model call.

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
- WP6 companion, done 10-29 (1b22108): 40 phrases tried on the 10-28 uncut photo. "yellow flower clusters" outlines the goldenrod heads (7.2 %), "vegetation" one mask over all plants (91.8 %); no phrase finds ogi (grass, reed, plume, silver grass, miscanthus, long leaves ...). Both added to uncut's nouns, the record re-measured (AI lines unchanged), the noun prompt told what worked. The basis line now says per plant what SAM measured and which shares are only the AI's reading; the proposal was re-run. Still open: a phrase for ogi, to try on the next photos.
- Done: tests pass, `sample/records/_proposals/uncut/<date>-cut.md` exists from a real run, README "Daily use" gets the two lines, committed. Then the farmer cuts.

## WP9: connect from your own AI (MCP server)

The farmer and the buyer use the AI they already have. fieldnotes serves its functions as MCP tools; the Flet app stays the way photos and voice get in. **9a** (the farmer's tools, `say`, the README section) is this hackathon's work. **9b** (`export`, `--buyer`) is the selling side and is held: it goes to a Claude hackathon if there is one, else into 11-02.

- Dependency: `mcp>=2.3` (the Python MCP SDK; in 2.x `FastMCP` is named `MCPServer`) in `pyproject.toml`. Module `src/fieldnotes/mcp_server.py` (not `mcp.py`). CLI `fieldnotes mcp [--http [--port 8551]] [--buyer]`: stdio by default; `--http` serves Streamable HTTP on the LAN; `--buyer` registers the read-only tools only. `--root` applies as everywhere.
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
- Real check: `claude mcp add fieldnotes -- <abs>/.venv/bin/fieldnotes --root <abs>/sample mcp`, then ask Claude Code to list the fields and read `uncut` (for 9b later: a `--buyer` run that asks "was fertiliser used?"). README section "From your own AI" with the config for Claude Desktop (`claude_desktop_config.json`), Claude Code and Muse Code. Muse Code takes MCP servers (dev.meta.ai, muse-code/extending): `mcp_servers` in `~/.config/muse/settings.json` (`"schema_version": 1`), transport `stdio` (command, args, env) or `streamable_http` (url, headers), plus `enabled` and `mode`.
- Done: tests pass, the real check with Claude Code done once, README section, committed.

## WP10: lookup, Japanese primary data (GSI) — 2026-10-30

**Done 2026-10-30, ba2615b** (`lookup_jp.py`, `tests/test_lookup_jp.py` with recorded fixtures, 78 tests). Departures from the brief, accepted: faults are their own key `faults_jp` so the 活断層図 and the hazard portal fail independently; the 活断層図 tiles are a scanned raster without names, so the red lines are found by colour (nearest line, and the nearest on the other side; 2 km at z15, else 4 km at z14; the line says how far was searched); the landform raw JSON keeps only the polygon the point falls in. Real runs: Ishii (高川原, 7 m on the 1 m laser DEM, 氾濫平野, nearest fault 3.1 km SW, outside the 土砂災害警戒区域, **inside** the 洪水浸水想定区域 at 想定最大規模) and Niihama (萩生, 97.1 m, 更新世段丘, faults 210 m S and 1.1 km N, both zones outside; matches the hand check). GSJ seamless still in maintenance. README lists both 出典 lines. The Niihama farm folder exists only in Opus's scratchpad until the farmer says where it lives (outside the public repo unless the owner allows publication).

**Why.** `lookup` feeds `site_background`, which every reading and the cut proposal rest on. For the second farm (新居浜市萩生, 33.9124, 133.2641) the world sources failed: the GSJ seamless geology API was in maintenance, Macrostrat answered "intrusive rock" (wrong: it is the Izumi Group, Tsutsumi et al. 2003), SoilGrids had no value. Opus's test on 10-30 (coordinates only, before any photo; answers scored against primary sources) showed that both models guess the soil wrong, Opus with confident names, Muse with cautious emptiness, and that five items settle the place, all fetchable from the coordinates alone. Better data in `lookup` improves both readers directly, and it is the product's line: a specialist source, not the general model's guess.

**Scope, Japan only (`site.country == "JP"`), four sources, each a `data` line in `records/lookup.md` with its source URL and the raw answer kept as `records/lookup/<key>.json`, in the form the existing lines use (`- \`data\` ... — 国土地理院 <API or tile>, <url>`):**

1. `address_jp`: 国土地理院 reverse geocoder → the 大字 (e.g. 萩生). New section "Place", first.
2. `elevation_jp`: 国土地理院 標高API → elevation (1 m laser DEM where it exists; the answer says which DEM). Keep the Open-Meteo line too; two lines, two sources.
3. `landform_jp`: 国土地理院 vector tile 地形分類 (`experimental_landformclassification1`, z14 GeoJSON) → the class of the polygon the point falls in (e.g. 台地・段丘, 更新世段丘). Point-in-polygon; fetch the neighbouring tiles when the point is near a tile edge.
4. `hazard_jp`: 国土地理院 活断層図 tiles (afm) and ハザードマップポータル tiles (disaportaldata): distance and direction to the nearest active fault line, and to the nearest 土砂災害警戒区域 and 洪水浸水想定区域, with "the field is inside / outside" said plainly. New section "Faults and hazards". The nearest fault's name when the data carries it.

Not in this package: 5, the 農研機構 日本土壌インベントリー (no point API; whether tiles or a download serve it is unknown). Write what was found about how to fetch it in the commit, and leave a `hypothesis` line in lookup.md naming the source so the farmer can check the map by hand. No change to non-Japan lookups, to weather, or to the reading prompts: `site_background` already takes every `data` line of lookup.md, so the readers get these without code.

**Rules.** A source that is down gives the existing "(not reached on <date>...)" line, never an exception out of `lookup`; timeouts short (10 s) so a slow tile server does not stall `init`. Attribution as the terms require: 国土地理院 content with 「出典：国土地理院」 (and the API or tile name), hazard portal tiles with 「出典：ハザードマップポータルサイト」; one line in the README's data-sources list each. Distances in m under 1 km, km above.

**Tests, offline:** fixtures recorded from the real answers of 10-30 for the Niihama point (address 萩生, elevation 97.1 m, landform 台地・段丘, 石鎚断層 ~200 m S, 岡村断層 ~1.1 km N, 土石流警戒区域 154 m, 洪水浸水想定 298 m, both outside); point-in-polygon and nearest-line distance checked on those fixtures, including a point near a tile edge; a down source. Then one real run on `sample` (Ishii) and one on the Niihama farm; commit `sample/records/lookup.md` and the raw JSON with the run noted in the commit.

**Budget and order.** Half a day. Today (10-30) in the idle time, after whatever comes first: the farmer's ✓/✗ on the cut proposal, and the real-voice check and `init` of the second farm when the Niihama recordings and photos arrive. Hard stop: the evening of 10-31. Before WP7 (which is mostly the planner's docs). The Glimmer language fix stays on 11-02; 9b is decided by the farmer today.

**WP10b, the map-sheet report (2026-10-30, Opus's proposal, accepted).** The point's formation name ("terrace deposits") does not say what rock the gravels are; the text of the 1:50,000 地質図幅 report does (新居浜 2013, §8.3: the terrace and fan gravels at 萩生 are almost all crystalline schist, with the Aira-Tn and Akahoya ashes between them; Gemini's "also Izumi Group" was wrong). The parent rock decides the soil's behaviour (schist soils are high-CEC; the Ehime fertiliser standard 令和8年度 p. 60 gives 110–140 kg/10a of dolomitic lime per pH unit against 70–80 for granite and Izumi sandstone soils; weathering gives vermiculite-like clay from chlorite and sericite, Shimoda 1979). So, Japan only, one more key in `lookup_jp.py`, `sheet_jp`: compute the 1:50,000 sheet from lat/lon (15′ of longitude by 10′ of latitude, named by the 1:200,000 sheet and its number), look the sheet up in the 産総研 catalogue, and write one `hypothesis` line in the Geology section: the sheet name, the report's year and PDF URL when one is published ("Parent material: not looked up. The 1:50,000 report 新居浜 (2013) describes the gravels here; read §8.3"), or "no report published for this sheet" when the catalogue has none. The catalogue is an offline fixture in the tests, with the sheet arithmetic checked on the Ishii and Niihama points and on a point at a sheet corner. No table that derives soil properties from parent rock (the only primary source is a prefectural standard), and no advice line about what to measure: that is for the reading model and the farmer, not for `lookup`. What Opus found about 萩生 goes into that farm's `site.md` as the farmer's own knowledge lines, with the sources, once the farmer says where the folder lives. Half a day, today in the idle time, after the real-voice check if the recordings arrive first; hard stop 10-31 evening.

Done 2026-10-30, 3c59854 (81 tests). `lookup_jp.sheet` (key `sheet_jp`), `sheet_cell` for the arithmetic (a point on an edge belongs to the east or south sheet). The line has three forms: report PDF, map without report, sheet unpublished; Hokkaido reports point at 道総研. Departures, accepted: the sheet is named by the 産総研 catalogue number (13［高知］-040), not the international 1:200,000 number; the line says "read its section on the unit at this point" since the section number is not machine-readable. Known fragility, by design: the catalogue is read from the index-map rectangles of the 14 regional catalogue pages (geology4-N.html), whose pixel grid Opus calibrated against 国土地理院 place names (30 towns, all named matches correct); the island pages 9 and 16 are irregular and give "not in the index map"; a page that cannot be read gives "not reached", distinct from "no sheet". If 産総研 changes the page layout, the line degrades to "not reached", never to a wrong sheet silently (the tests pin the fixture of page 13).

## WP11: the parcel and the map (2026-10-30, the farmer's request, Opus's proposal)

**Why.** The farmer: "use the 筆ポリゴン, the registry maps and 全国農地ナビ too, so the state of the field can be shown as a picture." Opus checked the sources on 10-30: the 筆ポリゴン (農林水産省) are served per point from a public ArcGIS FeatureServer (`FudePolygonTemp_2026`, GeoJSON by point query, no national download needed), with `land_type` (100 田, 200 畑, by visual reading of satellite images), the year and a history; the Ishii field lies in one parcel of about 600 m², read as 田 in 2020; the Niihama plot is a small garden beside a house and lies in no parcel. The 登記所備付地図 (法務省) are parcel-number boundaries tied to ownership and in areas without 地籍調査 use arbitrary coordinates: **not used**. 全国農地ナビ has no public API: a `reference` link line only.

**Terms, read by the planner on 10-30 (筆ポリゴンの利用規約, enacted 2022-10-17, last updated 2026-09-29, conforms to 政府標準利用規約 2.0, CC BY 4.0 compatible):** free use including copying, public transmission and adaptation, commercial use allowed. Required: the source line in the form 「出典：「筆ポリゴンデータ（<公開年度>年度公開）」（農林水産省）（<年月日>に利用）」, and when the data is edited or processed, say so (「…を加工して作成」) and never present it as if the state made it. The terms also require passing on to end users that the polygons are reference information for the position and shape of farmland, made by hand over aerial photos for the 面積調査, and show neither 筆界 nor rights. So the polygon may go into the public `sample` with those lines; the lookup.md line carries the source and the caveat, the README the source line and the caveat sentence. The 公開年度 in the label comes from the dataset, not from today's date.

**11a, `parcel_jp` in `lookup_jp.py` (half a day, today in the idle time).** One `data` line in a new section "Parcel": the parcel the point falls in, its area in m² (geodesic, or the Web-Mercator area corrected by cos²), 田 or 畑 with the year it was read, the parcel id, and how many parcels lie within 100 m with the 田/畑 split; "the point lies in no parcel" when none. The outline as GeoJSON in `records/lookup/parcel_jp.json`. One `reference` line linking 全国農地ナビ at the point. Tests on recorded fixtures for Ishii (in a parcel) and Niihama (none), plus the area arithmetic. Real runs on both; commit `sample`'s lines and raw JSON.

**11b, the plots as polygons (the farmer, by the morning of 11-01).** `records/fields/<field>.geojson`: one Feature per plot (row1, mix1, uncut), property `field`, drawn by the farmer on geojson.io over the aerial photo (five minutes) or given as corner points for Opus to write. Opus fixes the format, writes the loader and one test, and documents it in the README. When a field has no polygon, the map uses the parcel outline and labels it with the field name; nothing fails for want of a polygon.

**11c, `fieldnotes map` (one day, 11-01; must be done by the evening of 11-02 for the video).** `fieldnotes map [--date <day>]` → `records/map-<date>.png`: the 国土地理院 aerial photo (today's) under the parcel outline and the plots; each plot filled by the cover of its latest reading (SAM's share of the dominant plant, grey when there is no reading), outlined when a proposal awaits the farmer's ✓/✗, labelled with the field name, the dominant plant and the days since the last `work` line. The 1960s–70s photo as a second panel if it costs an hour, else not. The app shows the latest map in 読む; a tab only if cheap. The MCP `site` tool returns the map's path. Attribution: 「出典：国土地理院 空中写真」 added to the GSI line in the README. Tests: the drawing on a fixture (two plots, one reading, one proposal) checked for the files written and the labels, no pixel comparison.

**11a done 2026-10-30, d4ed8c4.** The source line is formed from the dataset's `issue_year` and the day of use, ends with 「を加工して作成」, and carries the caveat in the same line; README has the source line and the caveat sentence. Niihama, corrected point from the farmer (33.9123365, 133.2644683, about 30 m ESE of the first point; "most of the photos are of this field"): a parcel of 1517 m² read as 田 in 2020, 98.6 m on the 1 m DEM, 更新世段丘, faults 200 m S and 1.1 km N, 土石流 zone 150 m S, flood zone 310 m SW; the soil inventory, checked by hand, says 礫質水田化疑似グライ土 H2c1p2 (gravel within 60 cm), where the first point (the garden by the house, in no parcel) was 陸成未熟土. The second farm's folder is still in Opus's scratchpad until the farmer names its place.

**Order for Opus:** the real-voice check and the second farm's `init` when the recordings arrive > 11a today > 11c on 11-01 (after the farmer's polygons; the parcel outline when they are not there yet) > the Glimmer fix 11-02 > 9b on 11-02 if the farmer chooses it. 11c is the one piece here that changes the video: a picture of the field's state is worth a sentence in the script.

## WP12: what the app computes and what the AI fills in (2026-10-30, the farmer's direction, Opus's proposal)

**The farmer's direction (10-30):** not for my own field but for any field. Put as much as possible in the app; only what the app cannot compute is left to the AI (Muse, this time). Then check with today's photos. Then check with the records over days.

**What happened by hand on 10-30 (recorded in `sample/records/site.md`, 7156d07 and b4c1878):** a Gemini Deep Research report on the Ishii field was checked against primary sources and found wrong four times (natural levee → the GSI landform class says 氾濫平野; sandy loam with good drainage → the soil inventory says 細粒質水田化褐色低地土; silent on the flood zone the field is inside; 麻名用水 → the farmer's correction 高川原用水, confirmed in 阿波学会紀要 32). The farmer's own hypothesis (the big floods pushed water to the outside of the 飯尾川 bend) was checked: OSM puts the field on the outside of a ~100° bend, 62 m from the river; DEM5A with the plain's tilt removed puts the outside 0.2–0.5 m above its surroundings; the inundation layers cover only the national river's levee failure (L1 0.5–3 m, L2 5–10 m), the prefectural rivers' layer is empty. Three of the four errors are findable from `lookup` data alone; the fourth needed the farmer.

**Before the deadline (in this order; nothing of this on 11-02, which stays for the Glimmer fix, 9b if chosen, and the README):**

- **12a `soil_jp`, 10-31, half a day.** The 農研機構 日本土壌インベントリー map tile at the point (`/tile/figure/15/x/y.png`) read by pixel colour against the published legend (`js/figureRGB.js`: RGB → code, name, description) → one `data` line in Soil: the soil group and code, with "contains errors (農研機構's disclaimer)" in the line; replaces the hand-check `hypothesis` line. Terms, read by Opus on 10-30 at the farmer's request (農研機構『デジタル土壌図 活用マニュアル』2019-12, §3, and the site's help.pdf): the digital soil map is open data under CC BY 4.0, adaptation and commercial reuse allowed; credit 「農研機構、日本土壌インベントリー」, and published results say they used 農研機構日本土壌インベントリー (NARO, Japanese Soil Inventory); disclaimer on errors. Use only what 農研機構 serves (the tiles and figureRGB.js, or the prefectural Shape files); never the 日本土壌協会 CD-ROM data the farmland part derives from. One tile per point. The README's sources get the credit line and the manual's URL. Fixtures: the tile and legend for Ishii and Niihama; a colour not in the legend gives "not in the legend", not a guess.
- **12b `river`, 10-31 only if 12a is done by noon, else after the deadline, half a day.** From OSM (world-wide): the nearest river or stream, its name, the distance, which bank, and for a bend of more than ~60° within 300 m whether the field is on the inside or the outside. One `data` line in Terrain with the OSM ids.
- **B1, no code.** Checking an outside AI's report is the own AI's job through MCP: `site` returns the site and lookup lines; the farmer pastes the report into their own AI and asks it to sort the claims into agrees / conflicts / no data against those lines; what holds goes into `site.md` by hand, as on 10-30. One paragraph in the README ("From your own AI") and an optional scene in `docs/demo.md`; no `check-report` command.

**12a done 2026-10-30, eff7a89 (85 tests).** Only colours that match figureRGB.js exactly are used (the site itself takes the nearest colour, but neighbouring classes can differ by one step); Ishii 細粒質水田化褐色低地土 (F4c1t1), Niihama 礫質水田化疑似グライ土 (H2c1p2); the earlier hand reading 陸成未熟土 at the first Niihama point came from clicking beside the point.

**12c and 12d, checking the hypotheses with photos and then with records (the farmer, 2026-10-30, to Opus: "go as far as checking with photos for real; for the records, build it and start"). 10-31, one day; ahead of 12b.** One mechanism in two steps, so that the expectation is written before any photo is seen and cannot be fitted to it:

1. **`fieldnotes expect <field>`, text only.** For every `hypothesis` line in `records/site.md` (numbered h1, h2 ... in order of appearance, each line keeping its first words as a label so a renumbering shows), the reading model writes what a photo of this field would show if the hypothesis holds, what it would show if it fails, and whether a photo can tell at all (a flood 2000 years ago or underflow at 4 m: "not visible in a photo"; such lines are kept but not checked). Saved in the proposal file shape to `records/_checks/<field>/expect.md` (front matter: field, date, model, the site.md lines it was made from), lines `- h3: holds: ...; fails: ...; visible: yes | no [conf]`, markable with `fieldnotes mark ... --proposal expect` and editable by the farmer. Re-run only when site.md's hypotheses change.
2. **`observe` adds the check lines.** When `expect.md` exists, `observe` (CLI and the MCP tool, no new tool) shows the model the day's photos with the expectations and appends to the day's record a section `## Checks (<model>)` with one line per visible hypothesis: `- h3: agrees | disagrees | cannot tell: <what was seen, in the photo's own terms> [conf]`, parsed by `OBS_LINE`, marked ✓/✗ like any line, kept through re-runs like the farmer's other marks. **12c** is the first such run on the latest photos of the Ishii fields (10-30's or 10-31's); **12d** is the same lines on every later `observe`, plus one column per hypothesis in `fieldnotes timeline` (agrees / disagrees / cannot tell / ✓ ✗ by day). No separate evidence file.

Rules: Spark, `in_language`; the two steps never share a call; a hypothesis with "visible: no" never gets an "agrees". Tests offline with `FakeModel` (expect file shape, the checks section, marks kept on re-run, the timeline column). One real run on `sample` (expect, then observe on the latest photos), committed with the result noted. Half a day each; if 12d's timeline column does not fit on 10-31, the record lines come first and the column goes to 11-02 with the README.

**After the deadline (kept here so they are not lost):** 12b river; relief from DEM5A (the field's height against the plain with the tilt removed, low bands like old channels; drawn on the map) — only on 11-01 if `fieldnotes map` is done early; hazard detail (L1/L2 depth classes, national vs prefectural river); B2 questions to the farmer where data is missing, answered by voice into records.

## WP7: the demo — timeline, README, script

- `timeline.py` (minimal form done in 2a07572, tests in ef2cbf3): `timeline(field, records_root, photo_root, since=None) -> str`, Markdown, one block per date (oldest first): the photos (relative paths), weather in one line, the `overall` line with its verdict, the `work` and `seen` lines, the count of ✓ / ✗, any proposal of that day (its `summary` line and verdict). CLI `fieldnotes timeline <field> [--since DATE]`. The MCP `timeline` tool calls the same function. An app view only if time remains.
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
| 6 | real runs on the farmer's photos daily; SAM nouns and prompts tuned (10-29, 1b22108: goldenrod found by "yellow flower clusters", ogi by nothing yet); second farm (Niihama) from `init`; Glimmer language checked (10-29: still English, fix queued) | 1 | Opus + farmer | daily to 11-02 |
| 7 | timeline, README, demo script | 1, 6, 8, 9 | Opus (timeline) / planning session (README, demo.md) | 11-01 – 11-02 |
| 8 | cut proposal | 1 | Opus | done, cf490d7, basis per plant 1b22108 (real run: `sample/records/_proposals/uncut/2026-10-29-cut.md`; the farmer's ✓/✗ and the cut follow on 10-30) |
| 9a | MCP server for the farmer's own AI: `fields`, `read`, `observe`, `say`, `mark`, `propose`, `timeline`, `site`; README "From your own AI" | 1, 2, 8 | Opus | done, 2a07572 (real: stdio and `--http` with the SDK client; a Claude Code session itself still needs the farmer's sign-in) |
| 9b | `export`, `--buyer` (selling) | 9a | Opus | **held**: Claude hackathon, else 11-02 |
| 10 | `lookup` for Japan: 国土地理院 address, 1 m elevation, landform class, fault and hazard distances; NARO soil deferred | 1 | Opus | done, ba2615b (real runs: Ishii and Niihama; 78 tests) |
| 10b | `lookup` for Japan: the 1:50,000 地質図幅 report for the point as a `hypothesis` line (parent rock of the gravels) | 10 | Opus | done, 3c59854 (81 tests; Niihama → 新居浜 13［高知］-040 (2013) with the report PDF; Ishii → 13［高知］-033 unpublished) |
| 11a | `parcel_jp`: the 筆ポリゴン the point lies in (area, 田/畑, neighbours), 全国農地ナビ link | 10 | Opus | done, d4ed8c4 (83 tests; Ishii 602 m² 田 2020, 24 田 around; 全国農地ナビ takes no coordinates in a link, so a top-page link with "search the address above") |
| 11b | the plots as polygons, `records/fields/<field>.geojson` (format, loader) | 11a | farmer draws / Opus loads | by 11-01 morning |
| 11c | `fieldnotes map`: aerial photo + parcel + plots coloured by state | 11a, 11b | Opus | 11-01, done by 11-02 evening |
| 12a | `soil_jp`: 日本土壌インベントリー class at the point from the tile colour (CC BY 4.0, credit 農研機構) | 10 | Opus | done, eff7a89 (85 tests) |
| 12c | `fieldnotes expect <field>`: what a photo would show per hypothesis, then `observe` adds `## Checks` lines; first real run on Ishii | 1 | Opus | 10-31 |
| 12d | the same lines on every `observe`; a column per hypothesis in `timeline` | 12c | Opus | 10-31 (column by 11-02 at the latest) |
| 12+ | river, relief, hazard depth classes, B2 questions | – | – | after 11-05 (brief above) |
| – | Muse Code review (docs/muse-code.md Task 2) | – | farmer runs `muse` | by 11-02 |

Done for each package means: tests pass offline, one short real run when the package calls the API, the README section updated, and the work committed on main (or a branch) with a summary of what was and was not verified.

## Schedule to the deadline

| Day | Implementation (Opus) | Farmer |
|---|---|---|
| 10-29 Thu | WP8 cut proposal, tests, one real run on `uncut` | Niihama farm visit: photos, voice notes (the first real Japanese recording), three questions (who advises you, how do you sell, what would you pay to have solved). Evening on the LAN: `init` the second farm, send, `observe`, `voice` |
| 10-30 Fri | real-voice check and second farm `init` when the Niihama recordings arrive; WP10 lookup JP in the idle time | morning: ✓/✗ on the cut proposal; cut, or reject with a reason; a stick of known length in the before photo; daily photos; decide 9b |
| 10-31 Sat | WP12c expect + checks on the latest photos, 12d the lines on every observe and the timeline column; daily runs | cut if not yet; photos of the cut plot; the 1 m pin pole arrives: mark its spot and the standing spot; draw the plots on geojson.io |
| 11-01 Sun | WP11c `fieldnotes map` | photos; planning session: `docs/demo.md` (add the map), README structure |
| 11-02 Mon | README final, code tidy, nova's fork checked for parts to merge; WP9b only if selling stays in this hackathon | Muse Code Task 2 review; photos |
| 11-03 Tue | – | video: field footage, screen recording from the own AI, edit |
| 11-04 Wed | buffer | submission form (team members added here; public repo pushed) |
| 11-05 Thu 11:00 JST | **deadline** | |
