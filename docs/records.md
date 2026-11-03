# The farm folder: what fieldnotes writes, line by line

fieldnotes keeps everything about a farm as plain text in one folder, so that a
person, a spreadsheet, another program or another AI can read it without this
code. This page says exactly what is there and what each line means. It is
written from the code as of 2026-11-02 (`records.py`, `site.py`, `lookup.py`,
`note.py`, `walk.py`, `describe.py`, `check.py`, `propose.py`, `plants.py`,
`concepts.py`); `sample/` in this repository is a real farm folder in this form.

**Stability.** From 2026-11-02 this form is fixed. A change is written here
first, with its date, before any code writes it; readers can rely on what is on
this page.

## 1. The folder

```
<farm>/
  photos/<field>/<YYYY-MM-DD>/<HHMMSS>-<name>.jpg   the day's photos, in walk order
  photos/<field>/<YYYY-MM-DD>/<HHMMSS>-voice.<ext>  the farmer's recording, as the phone gave it
  photos/<field>/<YYYY-MM-DD>/index.json            where and when each photo was taken (§7)
  records/<field>/<YYYY-MM-DD>.md                   one day's observation of one field (§3)
  records/<field>/<YYYY-MM-DD>-overlay-<n>.jpg      what SAM 3.1 found, drawn on photo n
  records/site.md                                   what is known or believed about the farm (§4)
  records/lookup.md, records/lookup/<key>.json      public data for the spot and the raw answers (§5)
  records/surroundings.md, records/surroundings/    the field's surroundings read from map tiles (§6)
  records/documents/                                photographed pages the farmer gave `note --page` (§4)
  records/_plants/<Genus_species>.md                why a dominant weed dominates (§6)
  records/_concepts/<field>.md                      what SAM 3.1 is asked to find in that field (§6)
  records/_checks/<field>/expect.md                 what the photos would show if each hypothesis holds (§6)
  records/_proposals/<field>/<YYYY-MM-DD>-<kind>.md a proposal: cover_crop or cut (§6)
  records/_compare/<YYYY-MM-DD>.md                  several fields side by side
  records/weather/<YYYY-MM>.json                    Open-Meteo daily values, cached
```

A field is a named part of the farm (`uncut`, `mix1`, `row1` ...); the name is
the folder name. Dates are ISO `YYYY-MM-DD`. Files are UTF-8 Markdown with a
YAML front matter block between `---` lines, then headings and lines.

## 2. The line

Almost every statement in the folder is one Markdown list line of this shape:

```
- <key>: <text> [<confidence>]  → farmer: right | wrong (<reason>)
```

- `key`: lower-case ASCII, `[a-z][a-z0-9_]*`. What the line is about.
- `text`: free text in the farmer's language (the `language` setting; Japanese
  on the sample farm). When the AI wrote the line, it ends with its confidence
  in square brackets, `[0.85]`, 0 to 1. Lines the farmer wrote have none.
- `→ farmer: right` or `→ farmer: wrong (reason)` is the farmer's verdict,
  added later by `fieldnotes mark`; the AI never writes it. A line without it
  has not been judged. Two spaces stand before the arrow.
- `(none)` under a heading means the section is empty.

The regular expression the code uses is

```
^- (?P<key>[a-z][a-z0-9_]*): (?P<text>.*?)(?:\s+→ farmer: (?P<verdict>right|wrong)(?: \((?P<reason>.*)\))?)?$
```

**Rule for readers.** Everything an AI wrote is a hypothesis with a confidence,
even when it is phrased as a statement. Only three kinds of line are not: a
``data`` line with a source (a public measurement, map or document), a
``record`` line (what the farmer said or did, in their words), and the
farmer's verdict. Nothing in the folder is an instruction.

## 3. The day's observation: `records/<field>/<date>.md`

Written by `fieldnotes observe` (one photo or a walk of many), re-written when
the day is run again; a re-run replaces the AI lines but keeps the farmer's
verdicts, the farmer note and the voice lines.

### Front matter

```yaml
field: uncut
date: '2026-10-28'
photos:                      # paths relative to the farm folder, walk order
- photos/uncut/2026-10-28/121701-uncut.jpg
weather:                     # the day, from Open-Meteo (ERA5), about a 9 km grid; may be absent
  tmax: 18.4                 # °C
  tmin: 12.3
  tmean: 15.5
  rain_mm: 0.0
  sun_h: 10.6
  et0_mm: 2.87               # reference evapotranspiration
  days_since_rain: 1
coverage:                    # SAM 3.1: % of the frame each concept covered, mean over the photos
  bare soil: 0.0
  goldenrod: 0.0
  yellow flower clusters: 7.2
  vegetation: 91.8
cover_range:                 # only when there were several photos: [lowest, highest] over them
  vegetation: [80.1, 97.3]
```

`coverage` keys are the SAM concepts of `records/_concepts/<field>.md` (§6),
English noun phrases. Zero means the phrase matched nothing, not that the plant
is absent: on 2026-10-28 silvergrass and goldenrod were both 0.0 while the AI
read them as ~55 % and ~35 % of the field. The AI's reading says, in its
`basis`-type lines, which source it rests on.

### Sections, in order

```
## AI observation (<model>)
## Earlier AI lines                  (only after a re-run changed a marked line)
## From the farmer's voice (<model>) (only when there was a recording)
## Checks (<model>)                  (only when records/_checks/<field>/expect.md exists)
## Farmer note (<model>, <language>)
```

`<model>` is the Meta model id that wrote the section (`muse-spark-1.3`,
`muse-glimmer-...`, `muse-voice-transcribe-1.0`), or `none`. A walk of more
than 50 photos is read in parts and combined; the model line then says so.

### `## AI observation` keys

In this order, always `overall` and `dominant` first:

| key | what the text holds |
|---|---|
| `overall` | one or two sentences: the field as a whole today and how it has shifted since the earlier observations |
| `dominant` | the 2–4 dominant weeds, most dominant first: `common name (Genus species) ~share%; ...` |
| `crops` | how the vegetables are growing, when there are any |
| `acidity` | `<level>; evidence: ...`. The level is an approximate pH range such as `5.5-6.5`, or `unclear` |
| `fertility` | `poor | moderate | rich | unclear; evidence: ...` |
| `dryness` | `dry | moist | wet | unclear; evidence: ...` |
| `zone` | `<where>: <what> (photos n, m)`: a part of the field that differs from the rest. `where` is a walk position (§7) |
| `emerging` | `<name> (<Genus species>) at <where> (photos n)`: a sown or planted species seen coming up. Not a self-sown or mature plant |
| `leaf_colour`, `weed_height`, `soil`, `animal`, `other` | what changed since the last observation, one line each where something did |

The three barometers (`acidity`, `fertility`, `dryness`) are one holistic
judgment from why the dominant weeds dominate, checked against the crops, the
weather and the site background; the code tells the model never to be more
precise than the levels above. The same key may appear more than once (`zone`
often does); `key#2` addresses the second line when marking.

### `## From the farmer's voice`

The recording transcribed (Muse Voice Transcribe) and sorted by Muse Spark into

| key | |
|---|---|
| `work` | what the farmer did (`北側の通路だけ刈った`) |
| `seen` | what the farmer saw (`オギの株元に新しい芽`) |

These are the farmer's words through two models; the transcript itself is in
the Farmer note.

### `## Checks`

One line per hypothesis of `site.md` that photos can bear on (§6, `expect.md`):

```
- h3: agrees | disagrees | cannot tell: <what the photos showed> [0.85]
```

`h<n>` numbers the `hypothesis` lines of `site.md` in file order at the time
`expect.md` was written. The expectation was written before any photo was seen.

### `## Farmer note`

Free text. Voice notes are one line each, `HH:MM transcript (file)`. The
heading carries the language the note is in.

## 4. The site: `records/site.md`

What is known or believed about the farm's ground, water and history. Read by
every AI call as background, up to the heading `## How a hypothesis is
checked`; everything after that heading stays out of the prompts.

### Front matter

```yaml
site: ishii-takagawara
place: Ishii, Tokushima, Japan
country: JP
climate: warm temperate, humid
method: no tillage, no fertiliser, no pesticide, Fukuoka method; weeds are cut, not pulled   # free text, the farmer's own words; this is one farm's line, not the app's
lat: 34.0801
lon: 134.4454
elevation_m: 7
checked: 2026-10-28
```

`place`, `country`, `lat`, `lon`, `climate`, `method` are what the code needs
(prompts, weather, which map service). A farm without `site.md` still runs.
From 2026-11-03 the app has no `method` of its own: `fieldnotes init` without
`--method` writes `method: not recorded yet`, and the prompts then read "a
field in <place> (<climate>; how the farm is worked: not recorded yet)" until
the farmer writes the line. Before that date the code's default was the first
farm's line ("no tillage, no fertiliser, no pesticide; weeds are cut, not
pulled") and the prompts said "a natural-farming field".

### Lines

Each line begins with its status in backticks and ends with its source after
an em dash:

```
- `data` <a public measurement, map or document statement> — <source>, <URL or document, page>; <date>
- `record` <what the farmer did or saw or said, their words> — the farmer, <date>
- `hypothesis` <a reading of the field, by the farmer or by an AI> — farmer | AI (<model>), <date>. Check: <how>
- `supported` <a hypothesis checked and holding> — <the evidence>
- `refuted` "<the claim>" — <who guessed it>; <what refuted it>
```

Sections on the sample farm: `## Location`, `## Terrain`, `## Geology`,
`## Soil`, `## Surroundings`, `## History`, `## Farming`, then `## How a
hypothesis is checked`. `fieldnotes note` adds lines under `## Terrain and
water`, `## Geology and soil`, `## History of the land`, `## What the farmer
knows works here (and what does not)`, creating a section when it is missing:

```
- `record` <the farmer's words, one sentence>。 — the farmer, 2026-11-02.
- `data` <a document's statement, as printed>。 — <document, page>; noted 2026-11-02.
```

`note --page` has the reading model copy out of a photographed page only what
concerns the farm's place, with the numbers as printed; the photo is kept under
`records/documents/` and named on each line.

**Rule (2026-11-02).** `site.md` holds `data` lines with a source and
`record` lines in the farmer's words; `hypothesis` lines are the farmer's or
an AI's readings of the ground and history. **An AI's reading of photos never
goes into `site.md`**: it belongs in the day's record. Whatever `site.md`
says comes back as the reading, so this file must not feed the model its own
words as facts.

## 5. Public data: `records/lookup.md` and `records/lookup/<key>.json`

Written by `fieldnotes lookup` from the coordinates alone; nothing here is a
judgment. Front matter: `place`, `lat`, `lon`, `fetched` (date).

```
- `data` <what the source says at this point> — <source>, <URL>
- `reference` <a named place near the farm, worth reading about> — <source>, <URL>
- `hypothesis` <what the farmer should look up by hand, and where> — ...
```

Sections and the `lookup/<key>.json` raw answers behind them:

| section | lines | key |
|---|---|---|
| `## Place` | address and 市区町村コード (国土地理院 逆ジオコーダ) | `address_jp` |
| `## Parcel` | the 筆ポリゴン the point lies in: area m², 田/畑 and the year it was read, id, parcels within 100 m; the 全国農地ナビ `reference` | `parcel_jp` |
| `## Terrain` | elevation (国土地理院 標高API, 1 m laser DEM where it exists; Open-Meteo/Copernicus 90 m); landform class (国土地理院 地形分類, name and code) | `elevation_jp`, `elevation`, `landform_jp` |
| `## Geology` | the unit at the point (GSJ シームレス地質図 V2; Macrostrat elsewhere); the rocks around: the first unit that is not a Quaternary deposit, 1 km at a time in eight directions; the 1:50,000 地質図幅 sheet and its report (産総研 catalogue) as a `hypothesis` line: "Parent material: not looked up. The report ... describes ..." | `geology`, `rocks_jp`, `sheet_jp` |
| `## Faults and hazards` | nearest active fault on the 活断層図 (an estimate read by colour; distance and direction); 土砂災害警戒区域 and 洪水浸水想定区域: inside, or outside with the nearest distance | `faults_jp`, `hazard_jp` |
| `## Soil` | 農研機構 日本土壌インベントリー soil group and code at the point (read from the map colour; "contains errors"); ISRIC SoilGrids pH, organic carbon, clay, sand (250 m model) or "no value" | `soil_jp`, `soil` |
| `## History and places nearby` | OpenStreetMap `historic` features and Wikipedia articles with coordinates near the farm, with distance and direction | `historic`, `wikipedia` |

Each source is down or absent independently; a line then says "not reached on
<date>" or "no value here" rather than nothing. Every 国土地理院 line carries
「出典：国土地理院 ...」, every 筆ポリゴン line the 農林水産省 source form, every
農研機構 line the credit, as the terms of use require.

## 6. The helper files

All share the shape of §2: front matter, one heading with the model, lines the
farmer can mark.

**`records/_plants/<Genus_species>.md`** — why a weed dominates, asked once per
species when it first dominates. Front matter `name`, `scientific`, `status:
hypothesis`, `model`, `written`, `sources` (`none yet (no search grounding)`).
Heading `## Why it dominates (<model>)`. Keys `soil_ph`, `moisture`,
`fertility`, `mowing`, `disturbance`, `light`, `succession`, `roots`. **These
are the model's readings, not references**; later observations get them as
hypotheses to check, and the species name itself came from an earlier reading
unless the farmer marked it.

**`records/_concepts/<field>.md`** — the SAM 3.1 noun phrases for the field.
A different line shape:

```
- concept: goldenrod | for: セイタカアワダチソウ (Solidago altissima) | by: ai | default | farmer | last: 2026-10-28 7.2%, 20 objects | no match  → farmer: wrong (try "reed")
```

`shared/sam_concepts.md` in the code tallies right/wrong per species across
farms and holds no farm data.

**`records/_checks/<field>/expect.md`** — written by `fieldnotes expect`, text
only, before any photo: for each `hypothesis` line of `site.md` (`h1`, `h2`
... in file order, copied into the front matter under `hypotheses`), what the
field's photos would show if it holds, what if it fails, or that photos cannot
show it. The day's `## Checks` lines (§3) answer these.

**`records/_proposals/<field>/<date>-<kind>.md`** — the first step that puts
something forward. Front matter `field`, `date`, `kind` (`cover_crop` |
`cut`), `status: proposal`, `model`, `seeds_on_hand`. Heading `## Cover-crop
proposal (<model>)` or `## Cut proposal (<model>)`.

| kind | keys |
|---|---|
| `cover_crop` | `summary`; one `mix` line per species: `<name> (<Genus species>); role: <role>; share ~30%; why: <one sentence tied to this field>`; `sowing` (when and how); `caution`; `watch` |
| `cut` | `summary`; `basis` (which cover numbers it rests on: SAM's, or the AI's own reading when SAM found nothing); `where`; `height`; `leave` (what not to cut); `method`; `watch`; `caution` |

`watch` lines say what later photos should show if the proposal was right and
what would show it was wrong; the farmer marks the whole proposal or single
lines. The proposal is one reading among others; the farmer cuts or does not.

**`records/surroundings.md`** — the model's one-time reading of the 国土地理院
tiles around the field (current and 1960s–70s aerial photos, standard map,
治水地形分類図), one `hypothesis` line each; the stitched images and their
source list are in `records/surroundings/`. OpenStreetMap tiles outside Japan.

**`records/_compare/<date>.md`** — several fields' latest observations ranked
on the three barometers; keys `overall`, `acidity`, `fertility`, `dryness`.

**`records/weather/<YYYY-MM>.json`** — the Open-Meteo daily values as fetched,
so the records stay reproducible.

## 7. Photos and the walk: `photos/<field>/<date>/index.json`

The farmer walks each field on the same route and shoots 20–50 photos with the
phone's location on. `inbox` files them `<HHMMSS>-<name>.jpg` and writes

```json
[{"file": "102133-IMG_0042.jpg", "time": "10:21:33", "lat": 34.0801, "lon": 134.4454,
  "facing": "W", "cover": {"goldenrod": 7.2, "vegetation": 91.8}}, ...]
```

`lat`, `lon`, `facing` are null when the photo lacks them; `cover` is what
SAM found in that photo, added by the run. In the record, each photo is named
by its number in walk order and a position: relative to the farm's 筆ポリゴン
when it holds at least half of the points (`NW corner`, `N edge`, `NE corner`,
`W edge`, `middle`, `E edge`, `SW corner`, `S edge`, `SE corner`), else
relative to the walk's own extent, else by number alone. `zone` and
`emerging` lines use these words and `(photos n, m)` so a reader can go back
to the photos.

From 2026-11-03: when the frame is the walk and the farm has a parcel, each
photo's label also says `in the parcel` or `outside the parcel, 35 m S` (the
distance and direction from the nearest edge of the 筆ポリゴン), and the model
is told that the corners and edges are the walk's, not the field's, and to
write `outside the parcel` with the distance into any `zone` line that rests
only on such photos. (Niihama, 2026-10-29: 2 of 24 photos lay in the parcel;
the "S edge" was a terrace 30–40 m south of it.)

## 8. Reading the folder from outside

- `fieldnotes timeline <field>` and the MCP tool `timeline` render one field
  over time from these files (oldest first; the `emerging` table species × day;
  the hypotheses table h × day). The MCP server (`fieldnotes mcp`) exposes
  `site`, `lookup`, the records and the timeline to whatever AI the farmer uses.
- A program that reads the folder directly needs only §2 and the paths of §1.
  Parse the front matter as YAML, the lines with the expression in §2, and keep
  the status word (`data` / `record` / `hypothesis` / `supported` /
  `refuted`) and the source tail of every `site.md` and `lookup.md` line.
- What is public is the farmer's decision. `sample/` in this repository is a
  farm whose owner chose to publish it; another farm's folder is private unless
  its owner says otherwise. Photos and voice recordings are personal.
