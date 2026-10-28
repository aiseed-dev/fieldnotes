# Implementation design

What to build, how the parts connect, and the work packages handed to implementers. The why lives in [story.md](story.md), and the decisions made with the farmer live in [design.md](design.md). This file is the contract.

Deadline: 2026-11-05 11:00 JST (submission). Demo video recorded 11-03.

## Rules for every package

- Python ≥ 3.11, the package lives in `src/fieldnotes/`, and the venv is `.venv` (`.venv/bin/pip install -e .`).
- Match the existing code: small modules, plain dataclasses, plain-text records, docstrings that say why.
- **Records are plain text** that a person can read and edit: Markdown with YAML front matter and observation lines (`records.py`). Never add a database.
- Every AI output line can be marked by the farmer: `- key: text [conf]  → farmer: right|wrong (reason)`. Keep this line format; `records.OBS_LINE` parses it.
- Meta Model API: OpenAI-compatible at `https://api.meta.ai/v1`. The key comes from `llm.api_key()` (env `MODEL_API_KEY`, else `~/.config/fieldnotes/model_api_key`). Never print the key or log it.
- Tests run **offline**: put fakes in place of `chat` / SAM calls (see how earlier tests patched `describe.chat`). Add them under `tests/` with pytest. Spend real API credit only on one small smoke run per package, and say so in the commit.
- The UI is in Japanese. Code, comments and commit messages are in English. Commit messages end with `Co-Authored-By:` as instructed by the session.
- **Do not push.** The farmer pushes.
- Claims about the world (soil, plants, statistics) go into records only with a source that was read, never from memory (see `records/site.md`).

## Data layout

```
photos/<field>/<YYYY-MM-DD>/<HHMMSS>-<name>.jpg   filed by inbox.file_photo
photos/<field>/<YYYY-MM-DD>/<HHMMSS>-<name>.wav   voice notes (WP2/WP4)
records/<field>/<YYYY-MM-DD>.md                   one observation (records.Record)
records/<field>/<YYYY-MM-DD>-overlay-<n>.jpg      SAM overlay per photo (WP1)
records/_concepts/<field>.md                      SAM prompts per field (concepts.py)
records/_plants/<Genus_species>.md                why a weed dominates (plants.py)
records/_proposals/<field>/<date>-cover_crop.md   proposals (propose.py)
records/_compare/<date>.md                        field-to-field comparison
records/site.md, records/surroundings.md          site profile (data / hypothesis / refuted)
records/weather/<YYYY-MM>.json                    Open-Meteo cache
shared/sam_concepts.md                            SAM prompts shared across farms
```

## The observation pipeline (WP1 owns it)

`pipeline.run_observation(field: str, day: date, root: Path = ROOT, backend: Backend | None = None) -> Record`

1. Photos: `photos/<field>/<day>/*.jpg`, sorted. If there are none, raise.
2. Weather: `weather.daily_weather(day, root/"records")` goes into `rec.weather`.
3. Previous: `records.previous_records(root/"records", field, day.isoformat(), n=3)`.
4. SAM prompts: `concepts.ensure(records, field, species_in(previous dominant lines), backend)`.
5. Segmentation: `concepts.segment_field(rec, photo_root=root, records_root=records)` fills `rec.coverage`. Save one overlay per photo with `segment.save_overlay`.
6. Reading: `describe.observe(rec, previous, photo_root=root, records_root=records, backend)`. This also looks up ecology for newly dominant plants.
7. Prompts for next time: `concepts.ensure(...)` again, using today's dominant plants.
8. Save `records/<field>/<day>.md` and return the record.

Re-running the same field and day is allowed. It replaces the AI lines but **keeps any farmer verdicts and the farmer note** already in the file (merge by key and text; when the text changed, keep the old line with its verdict below a `## Earlier AI lines` heading). This matters because the farmer may run it twice.

`pipeline.mark(field, day, key, verdict, reason=None)` sets a verdict on an observation line. Concept verdicts go through `concepts.mark`.

## CLI (WP1)

`fieldnotes` console script (`[project.scripts]` in pyproject):

```
fieldnotes observe <field> [YYYY-MM-DD]          run the pipeline (default today)
fieldnotes show <field> [YYYY-MM-DD]             print the record
fieldnotes mark <field> <date> <key> right|wrong [reason]
fieldnotes concept <field> <noun> right|wrong [reason] [--replace NOUN]
fieldnotes propose <field>                       cover-crop proposal from the latest record
fieldnotes compare [YYYY-MM-DD]                  rank fields (latest record of each)
fieldnotes surroundings                          fetch maps + read once
fieldnotes app [--port 8550]                     the phone app
```

## Phone app (Flet web; WP3, WP4)

`src/fieldnotes/app.py`, one Flet app, served on the house machine and opened in the phone browser. The farmer shoots in the field and sends at home (design.md §1.13). Views, switched by tabs or routes:

1. **送る** (exists): field, date, pick photos, upload → `inbox.file_photo`.
2. **読む**: choose a field and date (those with photos). The 「読む」 button runs `pipeline.run_observation` in a background thread and shows progress; the UI must not freeze. Then show:
   - photos with SAM overlays (tap to enlarge);
   - the record's lines in order: overall, dominant, crops, acidity, fertility, dryness, changes;
   - on each line ✓ / ✗, and ✗ opens a reason box. Saved through `pipeline.mark`.
3. **名詞**: the field's SAM concepts with their last result, each with ✓ / ✗ and a replacement box (`concepts.mark`).
4. **声** (WP4): record in the browser and encode WAV (PCM16 mono 16 kHz) on the client, or upload an existing file. Then `voice.transcribe` saves the text as the record's farmer note, or as a ✗ reason.
5. **提案** (later): run `propose.propose_cover_crop` and show it with ✓ / ✗ per line.

Keep it usable on a phone at 375 px wide: large tap targets, no horizontal scroll.

## Consent to training (2026-10-28)

Muse Spark has a cheaper contributor model (`muse-spark-1.3-contributor`), and Meta may train on what is sent to it. The app asks the farmer on first launch, before anything is sent, and the gear in the top right changes the answer later. The CLI does the same with `fieldnotes consent [yes|no]`. The answer is kept in `~/.config/fieldnotes/settings.json` (`llm.training_consent`). `Backend.spark()` uses the contributor model only after a yes; until then it uses the standard model.

The farmer's view is that this app should be trained on: if AI learns natural-farming fields, the next farmer gets better readings. So 同意する is the recommended button, but the choice stays with each user.

## Which model reads (2026-10-28)

SAM always runs on api.meta.ai. The reading (describe, plants, propose, surroundings) goes to the model the farmer picks: Muse Spark on api.meta.ai (default), or Muse Glimmer on the house machine, so photos need not leave the house. The setting is `reader` in `settings.json` with `glimmer_url` and `glimmer_model` (defaults `http://192.168.100.6:11434/v1`, `muse-glimmer-30B`). `Backend.default()` follows it. The app changes it from the chip icon in the top right (with a 「つながるか試す」 button); the CLI with `fieldnotes reader [spark|glimmer] [--url] [--model] [--check]`.

Glimmer runs on the MS-S1 MAX as llama.cpp `llama-server` (ROCm build, gfx1151) with the official GGUF from `meta-models/Muse-Glimmer-30B-GGUF` (Q4_K_M plus the `mmproj` for images), alias `muse-glimmer-30B`, on port 11434.

## Voice (WP2)

`voice.transcribe(wav: Path, vocabulary: list[str] = (), language="ja") -> str` uses Muse Voice Transcribe (`muse-voice-transcribe-1.0`): `POST /v1/asr/transcribe`, multipart with a request JSON plus the WAV (at most 10 min, at most 32 MB), PUSH_TO_TALK mode, language bias Japanese, vocabulary biasing. **Read the API reference on dev.meta.ai before writing the request; do not guess field names.**

`voice.vocabulary(field, root)` builds the vocabulary from the field's dominant plant names, SAM concept targets and a fixed farm list (大根, カイラン, 子葉, 本葉, 刈り草, 草マルチ, 足跡, 鹿, 猪, オギ, セイタカアワダチソウ, クリムソンクローバー, ライ麦).

## Work packages

| WP | What | Depends on | Who |
|---|---|---|---|
| 1 | `pipeline.py` (run, mark, merge), overlays, CLI, pytest setup with offline fakes | – | Sonnet session |
| 2 | `voice.py` + its tests; one real smoke call on a short Japanese WAV | – | Muse Code (if installed), else Sonnet |
| 3 | App views 読む and 名詞, calling the WP1 functions by the signatures above | WP1 signatures (code may land in parallel) | Sonnet session |
| 4 | App view 声: browser WAV recording plus upload into `voice.transcribe` | WP2, WP3 | Sonnet, after 2 and 3 |
| 5 | Native capture app (`mobile/`), offline queue → sync | – | separate session (card proposed) |
| 6 | First real runs on the farmer's photos; tune SAM prompts and Spark prompts | photos, WP1 | main session with the farmer |
| 7 | Demo: a timeline page per field (photos, overall line, verdicts), README run guide, video script | 1, 3, 6 | main session |

Done for each package means: tests pass offline, one short real run when the package calls the API, the README section updated, and the work committed on its branch with a summary of what was and was not verified.
