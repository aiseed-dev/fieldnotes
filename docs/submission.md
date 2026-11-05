# Submission text (draft, 2026-11-03)

For the Meta Global AI Developer Hackathon form (Indie Developer track, theme *Build for Your World*). Written from the README and [story.md](story.md); nothing here is claimed that they do not say. Revised 2026-11-05 on the farmer's word (「提出を急ぐな。目的も見直せ。できていないところは、文章も変更しろ」): what is not done is said to be not done. Places marked （作者が選ぶ） are for the author to decide. Repository and video links are left blank.

## Project name

fieldnotes

## One-paragraph overview

fieldnotes is Muse plus Flet: Meta's models (SAM 3.1, Muse Spark, Muse Voice Transcribe) read a farmer's field, and a Flet phone app is where the farmer walks, marks and reads; the reading is kept as plain-text records at home. Farming today runs on things bought from outside: fertiliser from suppliers, and the know-how to use it from the co-op and the dealers. Every field has different soil and different weeds, so no single method can be handed down from above. Instead, AI reads each field — its terrain, geology, weeds and weather — and the farmer looks, works, and checks the AI against what actually happens. It is for any farmer, whatever way they farm: the author farms without fertiliser because they want to try Fukuoka's natural farming and want the records to show its gains and its losses; the app has no method of its own. The farmer walks the field with a phone and marks lines; typing can be replaced by talking. SAM 3.1 segments leaves, flower clusters and bare soil; Muse Spark reads the photos against the previous days and against public data about the land; Muse Voice Transcribe is wired to write down what the farmer says in the field (not yet used on a real recording). Every AI line can be marked right or wrong, and the corrections feed the next reading. There is no chat screen: the farmer connects from the AI they already use (Claude, ChatGPT, Muse Code ...) over MCP, and the records stay at home as Markdown that any person or model can read.

## What it does

- **The phone app is the main entrance** (Flet, Python; the command line and the MCP server are the same functions for scripts and for your own AI). Four views: Send (field, day, photos and a voice file from the phone; the walk as a strip in order under the GPS points on the parcel outline), Read (the photos, the SAM overlays, every AI line one row headed by its model and date with ✓ ✗ and a reason, the day's mark count, two readings of the same day side by side, and plain words where there is nothing: "No reading yet", "SAM found nothing for these prompts", "Voice not transcribed"), Land (`site.md` and `lookup.md` line by line with sources, the hypotheses checked day by day, and from the phone `init`, `note`, timeline, `expect`, `propose`) and Nouns (SAM's noun phrases, ✓ ✗ with a replacement). Dark screen, a QR code to open it, no keyboard beyond the reason box, no sign-in on the home network. The demo video's screens are captured from it.
- **Any farm, from one command.** `fieldnotes init` starts a farm folder with where it is. `fieldnotes lookup` fetches public data for the spot, each line with its source: elevation, bedrock, soil, history nearby; in Japan also the national sources (国土地理院 address, 1 m elevation and landform class, the nearest active fault, the hazard zones, the 筆ポリゴン farmland parcel, the 産総研 1:50,000 geological map sheet, the 農研機構 soil map). The farmer adds what they know with `fieldnotes note`, each line marked `data`, `record` or `hypothesis`. Outside Japan only the world maps today; the sources for the US and Europe are listed (WP14) and not yet built.
- **The field from many photos.** The farmer walks the field with the phone's location on and takes 20–50 photos. SAM 3.1 segments each photo; Muse Spark reads the whole walk in one request, each photo labelled with where it was taken, and says which parts of the field differ (`zone`) and what was sown or planted is coming up (`emerging`).
- **Checking hypotheses on the photos.** `fieldnotes expect` has the model write, before it sees any photo, what photos would show for each hypothesis about the land; every later `observe` answers `agrees`, `disagrees` or `cannot tell` per hypothesis, and the timeline shows the answers day by day.
- **Where to cut first.** For a plot left uncut for a year that now looks like abandoned farmland, `fieldnotes propose --cut` gives one place and one height to cut first, with the reason and what the next days' photos should show. One proposal was written (2026-10-29); it is not yet marked.
- **Photos and voice.** The phone's own recorder; Muse Voice Transcribe writes it down in the farmer's language; Muse Spark sorts it into what was done, what was seen, and verdicts on the AI's lines. Built and tested with mocked answers; no real recording has been through it as of 2026-11-05.
- **From your own AI.** `fieldnotes mcp` serves the tools (`fields`, `read`, `observe`, `say`, `mark`, `propose`, `timeline`, `site`, `note`) to Claude Code, Claude Desktop, Muse Code or any MCP client; `--http` for an AI on another machine in the house.
- **Records.** Plain Markdown with YAML front matter; what every file and line means is written in `docs/records.md`, so other programs and other AIs can read a farm folder. `pip install "fieldnotes-farm[app]"`.

## Meta models and products used

| Model | Use |
|---|---|
| `sam-3.1` (Meta Model API) | segments crops, weeds, bare soil and the field's own noun phrases in every photo → cover % |
| `muse-spark-1.3` (Meta Model API) | reads the photos against the previous days and the site's public data, in the farmer's language; sorts what the farmer said; writes the cut proposal and the expectations per hypothesis |
| Muse Glimmer 30B (local, llama.cpp) | the same reading on a machine in the house, so photos need not leave it; chosen with `fieldnotes reader glimmer` |
| `muse-voice-transcribe-1.0` (Meta Model API) | the farmer's recordings, language-biased, with the field's plant names as keywords |

Muse Code: （作者が選ぶ — the README names Muse Code only for commits that carry the line `Written with Muse Code`; on 2026-11-03 no commit on `main` carries it, so the README does not claim it）

## What Meta's models did well, and compared with other ways

Everything here is from the records in the farm folders (private, `~/farm/`; the lines are quoted as written), not from a benchmark. One field, one week, one farmer marking.

**Muse Spark 1.3 — reading a walk of 32 photos as one field.** On 2026-11-02 it took the day's 32 photos in one request and wrote, in Japanese, what is where with the photo numbers: `zone: SE cornerからS edge中央を通りmiddleへ続く帯: 当日刈られた刈り倒し帯で… (photos 1, 4, 25, 26, 27, 28, 29, 30, 31, 32) [0.85]`, three such zones, the dominant plants with shares, and an answer to each of 18 hypotheses about the land (agrees / disagrees / cannot tell, each with what it saw). It named the tall grass オギ (Miscanthus sacchariflorus) without being told; the same photos read the same evening by a general-purpose model (Claude, in the seed project) called it ススキ and the farmer marked that line wrong (「ススキではなくてオギ」). On a different farm (Niihama, 2026-10-29, 24 photos, `fieldnotes init` and nothing else) it found the spring at the N edge, the paddy remnant with rice stubble, the mulched onion beds and the goldenrod stand, each with its photos. It follows the language rule (the farmer's language, plant names with the Latin binomial); it read a walk of 32 photos in minutes on the Meta Model API.

**Muse Glimmer 30B at home — the same reading without the photos leaving the house.** It runs on a Ryzen AI Max+ 395 box with llama.cpp and gives a sensible reading, but 212 s for one photo (2026-10-29) and in English despite the language rule, where Spark answers in Japanese. So the house model is the privacy option and Spark the daily one; the code is the same, only `base_url` and `model` differ, and any OpenAI-compatible model can be put there.

**SAM 3.1 — concept segmentation per photo.** Three seconds a photo, prompted with the field's own noun phrases (`white feathery plumes` for オギ, `yellow flower clusters` for goldenrod, `bare soil` …) and the overlays show what it took. It is the right tool for cover; the numbers it gave on this field are not yet right: on 2026-11-02 the day's cover came out as leaf 3.2 %, white plumes 0.2 %, bare soil 0.1 %, while Spark's reading of the same photos says オギ ~40 %, goldenrod ~30 %, vine ~20 % and the farmer's eye agrees with Spark. The prompts were not tuned for a 2.5 m stand photographed from inside it, so the cover lines stay in the record as they are, unmarked, and the `concept` file shows `no match` for each prompt — the farmer can see it rather than have it hidden. Tested on 2026-11-05 on a copy of the folder: the same 32 photos with scene-level nouns give vegetation 86.7 %, grass 61.6 %, dry grass 13.8 %, cut grass 1.9 % (mean over the walk; up to 99.9 % in single photos), while `leaf` gave 3.2 % — the nouns were the problem, not SAM. Plumes and small flowers are still not found at this frame size; `sky` is (17 %), so the pipeline is sound.

**Muse Voice Transcribe 1.0.** The path is built (file the recording, transcribe with the field's plant names as keywords, let Spark sort it into work / seen / verdicts) and tested with mocked answers; as of 2026-11-05 no recording in the farm folders has been through it — the 11-02 `work` line was typed from the farmer's words. So nothing is claimed for it here beyond that it is wired in.

**Compared with other ways.** (1) *A general-purpose model reading the photos* (Claude, same photos, 11-01 and 11-02): stronger at reasoning over the land data — the hypotheses in `site.md` about the plough pan, the paddy seepage and the goldenrod on the dry side are its — and weaker at the plant in front of it (ススキ/オギ); Spark is the reverse. The records keep both, each marked by the farmer, never merged by a machine. (2) *Satellite indices* (Sentinel-2 NDVI, 10 m): say the field is green, cannot see under a 2.5 m canopy or name a plant, and give nothing for a 600 m² parcel day by day; the phone walk does. (3) *The farmer's eye alone*: it is the standard every line is marked against; what the models add is that the walk is written down the same evening, every day, with the photo numbers, so that a year later the change is there to read. (4) *A dedicated farm-vision model*: none that knows オギ from ススキ in Tokushima was found; the plant list grows from the farmer's corrections instead.

**What is not yet known.** Whether Spark's zone lines are right in the places the farmer has not marked (0 of 10 lines marked on 11-02); whether the SAM cover can be made right with better prompts; how Voice Transcribe does on a farmer's Japanese in the wind. These are the next week's work, not claims.

## Built during the hackathon

Everything in the repository was written during the event (26 Oct – 4 Nov 2026): the code under `src/fieldnotes/`, the scripts, the docs, and the sample farm's records under `sample/` (Japanese) and `sample-en/` (the same farm read in English). Two things existed before and are not used by the repository: a photo-alignment tool (`field-timelapse`) and a JMA-based weather site the author runs; the project's daily weather comes from the Open-Meteo archive.

## The field it was built on

The author's own field in Tokushima, Shikoku, just south of the Median Tectonic Line, where the author is testing Masanobu Fukuoka's natural farming (no tillage, no fertiliser, no pesticides). It has had no fertiliser for four years; one plot left uncut for a single year is now goldenrod and Amur silver grass (ogi) taller than a person. The tool reads such land and proposes where and how to cut first to bring it back into crops. What the records can show in the hackathon's days is the reading before the cut and the days after it; nothing more is claimed.

## Links

- Public repository: https://github.com/aiseed-dev/fieldnotes （the `origin` remote; the author pushes `main` before the form）
- Demo video (3 minutes): https://youtu.be/xw2kbu5pmWg (YouTube, public; uploaded by the author 2026-11-05 10:10 JST)
- Package: `fieldnotes-farm` on PyPI, https://pypi.org/project/fieldnotes-farm/ (0.1.0 published 2026-11-04 from the GitHub Actions Trusted Publisher workflow)

## Licence

AGPL-3.0-or-later.

## Form answers (2026-11-05 10:00 JST, the farmer filling the form: 「提出用フォームを埋めて行きたいです」)

- Team Name: aiseed.dev (the farmer, 10:03: 「チーム名は、aiseed.devにします」)
- Team Members: ysniji (Yasuhiro Niji)
- Track: Indie Developer
- Problem statement: Build for Your World
- Most Viral Track (X post): https://x.com/creativewebjp/status/2118156947979694226 (posted by the author from YouTube, 2026-11-05 10:45 JST)
- Project Description (under 3,000 characters):

```
fieldnotes — read your field from the photos of a walk, with Meta's models, kept as plain text at home.

The problem. Farming today runs on things bought from outside: fertiliser from suppliers, and the know-how to use it from the co-op and the dealers. Every field has different soil and different weeds, so no single method can be handed down from above. I built fieldnotes on my own field in Tokushima, Japan — a former paddy, no fertiliser for four years, one plot left uncut for a year that now looks like abandoned farmland — so that any farmer, whatever way they farm, can read their own field and keep the record themselves, nothing hidden and every line with its source.

What it does. The farmer walks the field with a phone and takes 20–50 photos. SAM 3.1 segments each photo (leaves, flowers, bare soil, the field's own nouns) into cover per concept. Muse Spark 1.3 reads the whole walk in one request, each photo labelled with where it was taken, against the previous days and against public data about the land (elevation, landform, geology, soil, the farmland parcel, local history — each line with its source), and writes what differs where in the field, what is coming up, and an answer per hypothesis about the land: agrees, disagrees or cannot tell. Muse Voice Transcribe is wired in to write down what the farmer says in the field, in the farmer's language. Muse Glimmer 30B runs the same reading at home when photos should not leave the house.

The AI is not a teacher. Every model line is a reading headed by its model and date, never shown as a fact; the farmer marks each line right or wrong with a reason, and the corrections feed the next reading. Two readings of the same day sit side by side, never merged by a machine.

The phone app (Flet, Python) is the main entrance: Send (photos and voice in; the walk as a strip under the GPS points on the parcel outline), Read (the SAM overlays, every AI line with ✓ ✗ and a reason, the day's mark count), Land (the public data line by line with sources, the hypotheses checked day by day, and from the phone: start a farm, add a note, timeline, expectations, a cut proposal) and Nouns (SAM's prompts, correctable). Dark screen, a QR code to open it, no keyboard beyond the reason box, no sign-in on the home network. The command line and an MCP server are the same functions, so the farmer's own AI (Claude, Muse Code, any MCP client) can read and mark the records too. Records are plain Markdown with a written format, readable by any person or model.

Honest state. On my field the walks of 11-01 to 11-03 are read but still unmarked; the voice path is built and tested with mocked answers and no real recording has been through it yet; SAM's cover came out near zero with the default prompts and right only with scene-level nouns. The real check is by growing.

Built during the hackathon: everything in the repository. pip install "fieldnotes-farm[app]". AGPL-3.0-or-later.
```

- Describe your use of Meta products to build the submitted project (10:25):

```
Three models on the Meta Model API (dev.meta.ai), each called from src/fieldnotes/: sam-3.1 segments every photo of a walk, one concept per request (leaves, flower clusters, bare soil, the field's own noun phrases), and the masks become cover per concept per day and the overlays the farmer sees in the app. muse-spark-1.3 reads the whole walk (20–50 photos, each labelled with where it was taken) in one request against the previous days and the land's public data, in the farmer's language, and writes the zone, emerging and per-hypothesis lines; it also writes the cut proposals and the expectations, sorts what the farmer said into work, seen and verdicts, and copies a photographed document page into the site record. muse-voice-transcribe-1.0 is wired in to write down the farmer's voice notes, language-biased with the field's plant names as keywords (built and tested with mocked answers; no real recording has been through it yet). Muse Glimmer 30B runs the same reading locally through llama.cpp on a Ryzen AI Max+ 395 box, so photos need not leave the house; the same code, a different base_url. Muse Code was not used to write the code (no commit carries its line); the README shows how to connect fieldnotes to Muse Code as an MCP client.
```

- Why are Meta's models important to your solution? (10:28):

```
Because a field cannot be read by one general model from a single photo. It needs specialist models that work together: a segmenter that takes the field's own noun phrases and returns masks, so the cover of each weed and of bare soil can be counted per day and corrected by the farmer (SAM 3.1); a vision-language model that takes 32 photos with their positions in one request and reads them as one field, in the farmer's language, against the previous days and the public data about the land (Muse Spark 1.3 — on 11-02 it named the tall grass ogi, Miscanthus sacchariflorus, without being told, and answered 18 hypotheses about the land from the photos); a transcriber that writes down a farmer's words in the wind with the field's plant names as keywords (Muse Voice Transcribe); and a model of the same family that runs in the house when the photos should not leave it (Muse Glimmer 30B through llama.cpp). One API, one key, one record format for all of them, and the same code for the cloud and the home model, is what let one farmer build this in ten days. And because these are readings and not facts, the farmer marks every line; the records keep the model's name on each one, so a wrong reading is a wrong reading, never the farmer's.
```

- Provide feedback from your experience using partner technologies (10:31; the Muse Code sentence removed on the farmer's word 「使っていない」):

```
What worked: the Meta Model API speaks the OpenAI chat format, so one code path serves Muse Spark in the cloud and Muse Glimmer in the house, and any other OpenAI-compatible model can be put in the same place; one key, one base URL. Muse Spark 1.3 took 32 photos with their positions in a single request and read them as one field, in Japanese, naming plants it was not told about. SAM 3.1 returns clean masks in about three seconds a photo.

What cost time: (1) SAM 3.1 is very sensitive to the prompt noun: with the obvious nouns (leaf, flower cluster, bare soil) the cover of a 2.5 m stand of ogi and goldenrod came out near zero; with scene-level nouns (vegetation, grass, dry grass) it was right. A note in the docs on how to phrase concepts for dense vegetation, and several concepts in one request, would help. (2) Muse Spark's limit of 50 images per request is not stated where I looked; I found it by hitting it, and now split long walks and combine the readings. (3) Muse Glimmer 30B on llama.cpp answers in English whatever the language instruction says, and takes about 212 s a photo on a Ryzen AI Max+ 395 box; the model is good, the speed and the language rule are the gap to Spark. (4) Muse Voice Transcribe: the request shape for a language bias plus keywords took some guessing; I would welcome an example with a non-English language.
```

- Why are Meta's models important — the version with the experience folded in (10:37, the farmer: the feedback belongs here, the partner field is for others' technologies, 「使っていない」):

```
Because a field cannot be read by one general model from a single photo. It needs specialist models that work together: a segmenter that takes the field's own noun phrases and returns masks, so the cover of each weed and of bare soil can be counted per day and corrected by the farmer (SAM 3.1); a vision-language model that takes 32 photos with their positions in one request and reads them as one field, in the farmer's language, against the previous days and the public data about the land (Muse Spark 1.3 — on 11-02 it named the tall grass ogi, Miscanthus sacchariflorus, without being told, and answered 18 hypotheses about the land from the photos); a transcriber that writes down a farmer's words in the wind with the field's plant names as keywords (Muse Voice Transcribe); and a model of the same family that runs in the house when the photos should not leave it (Muse Glimmer 30B through llama.cpp). One API, one key, one record format for all of them, and the same code for the cloud and the home model, is what let one farmer build this in ten days. And because these are readings and not facts, the farmer marks every line; the records keep the model's name on each one, so a wrong reading is a wrong reading, never the farmer's.

What I learned using them: the API speaks the OpenAI chat format, so one code path serves Spark in the cloud and Glimmer at home, and any OpenAI-compatible model can be put in the same place. SAM 3.1 returns clean masks in about three seconds a photo but is very sensitive to the prompt noun — with the obvious nouns the cover of a 2.5 m stand of ogi and goldenrod came out near zero, with scene-level nouns (vegetation, grass, dry grass) it was right — so the farmer can correct the nouns in the app. Spark's limit of 50 images per request I found by hitting it; long walks are now split and combined. Glimmer at home answers in English whatever the language rule says and takes about 212 s a photo on a Ryzen AI Max+ 395 box: the privacy option, with Spark as the daily one.
```
