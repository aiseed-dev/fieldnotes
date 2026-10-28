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
4. **Verify**: I speak a note in the field; **Muse Voice Transcribe** (Japanese) turns it into text; I mark each AI observation right or wrong.
5. **Record** everything as plain Markdown that any person or model can read later. Corrections feed back into the next day's prompt.

## What was built during the hackathon

Everything in this repository: `src/fieldnotes/` (segment, describe, verify, records, report), `scripts/`, `docs/`, and the daily records under `records/`.

## What existed before the hackathon

* `field-timelapse` — aligns hand-held photos to a reference frame (SIFT features, RANSAC homography). Used unchanged as step 1; vendored/linked separately so the boundary is visible in the history.
* A JMA-based weather statistics site I run; this project only *reads* daily values from it.

## Meta models used

| Step | Model | How |
|---|---|---|
| Segment | `sam-3.1` | Meta Model API, one concept per request, masks → cover % (`src/fieldnotes/segment.py`) |
| Describe | `muse-spark-1.3` | Meta Model API, several days' photos in one request, JSON out (`src/fieldnotes/describe.py`) |
| Describe (local) | Muse Glimmer 30B | Ollama on a Ryzen AI Max+ 395 box in the house; same code, different `base_url` (`scripts/setup-glimmer-server.sh`) |
| Verify | `muse-voice-transcribe-1.0` | Japanese, with vocabulary biasing for crop names |
| Development | Muse Code | used for parts noted in commit messages |

## Running

```bash
python -m venv .venv && .venv/bin/pip install -e .
# Meta Model API key (dev.meta.ai → API keys): either set MODEL_API_KEY,
# or keep it in ~/.config/fieldnotes/model_api_key (chmod 600), which is read when the variable is unset.
```

Daily use (photos are filed under `photos/<field>/<date>/` by the phone app, or put there by hand):

```bash
fieldnotes observe uncut 2026-10-28      # weather → SAM → Muse Spark → records/uncut/2026-10-28.md (+ overlays)
fieldnotes show uncut                    # the latest record
fieldnotes mark uncut 2026-10-28 dominant right
fieldnotes mark uncut 2026-10-28 overall wrong "it is uneven, not even"
fieldnotes concept uncut goldenrod wrong "finds ogi too" --replace "yellow flowers"
fieldnotes propose uncut --seeds "crimson clover, rye"
fieldnotes compare                       # rank fields by the newest record of each
fieldnotes surroundings                  # read the GSI maps once (--force to redo)
fieldnotes app --port 8550               # the phone app
```

`--root DIR` (before the subcommand) points at the folder that holds `photos/` and `records/`; the default is `$FIELDNOTES_ROOT`, else the current folder. If the `fieldnotes` command is not found, `.venv/bin/python -m fieldnotes ...` does the same (re-run `pip install -e .` to get the command).
Running `observe` again on the same day replaces the AI lines but keeps your right/wrong marks and note; a marked line whose wording changed moves under `## Earlier AI lines`.

Tests run offline: `.venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`.

### Phone app

```bash
.venv/bin/python -m fieldnotes.app        # http://<this machine>:8550, open it on the phone
```

Three views at the bottom: 送る (send photos into `photos/`), 読む (run the observation for a field and day, look at the SAM overlays, mark each AI line ✓ or ✗ with a reason) and 名詞 (the SAM noun phrases of a field, ✓ or ✗ with a replacement). Everything it shows or saves is a plain-text record under `FIELDNOTES_ROOT` (default: the current directory).

## Licence

AGPL-3.0-or-later.
