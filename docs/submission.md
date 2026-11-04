# Submission text (draft, 2026-11-03)

For the Meta Global AI Developer Hackathon form (Indie Developer track, theme *Build for Your World*). Written from the README and [story.md](story.md); nothing here is claimed that they do not say. Revised 2026-11-05 on the farmer's word (「提出を急ぐな。目的も見直せ。できていないところは、文章も変更しろ」): what is not done is said to be not done. Places marked （作者が選ぶ） are for the author to decide. Repository and video links are left blank.

## Project name

fieldnotes

## One-paragraph overview

fieldnotes is Muse plus Flet: Meta's models (SAM 3.1, Muse Spark, Muse Voice Transcribe) read a farmer's field, and a Flet phone app is where the farmer walks, marks and reads; the reading is kept as plain-text records at home. Farming today runs on things bought from outside: fertiliser from suppliers, and the know-how to use it from the co-op and the dealers. Every field has different soil and different weeds, so no single method can be handed down from above. Instead, AI reads each field — its terrain, geology, weeds and weather — and the farmer looks, works, and checks the AI against what actually happens. It is for any farmer, whatever way they farm: the author farms without fertiliser because they want to try Fukuoka's natural farming and want the records to show its gains and its losses; the app has no method of its own. The farmer walks the field with a phone and marks lines; typing can be replaced by talking. SAM 3.1 segments leaves, flower clusters and bare soil; Muse Spark reads the photos against the previous days and against public data about the land; Muse Voice Transcribe is wired to write down what the farmer says in the field (not yet used on a real recording). Every AI line can be marked right or wrong, and the corrections feed the next reading. There is no chat screen: the farmer connects from the AI they already use (Claude, ChatGPT, Muse Code ...) over MCP, and the records stay at home as Markdown that any person or model can read.

## What it does

- **Any farm, from one command.** `fieldnotes init` starts a farm folder with where it is. `fieldnotes lookup` fetches public data for the spot, each line with its source: elevation, bedrock, soil, history nearby; in Japan also the national sources (国土地理院 address, 1 m elevation and landform class, the nearest active fault, the hazard zones, the 筆ポリゴン farmland parcel, the 産総研 1:50,000 geological map sheet, the 農研機構 soil map). The farmer adds what they know with `fieldnotes note`, each line marked `data`, `record` or `hypothesis`. Outside Japan only the world maps today; the sources for the US and Europe are listed (WP14) and not yet built.
- **The field from many photos.** The farmer walks the field with the phone's location on and takes 20–50 photos. SAM 3.1 segments each photo; Muse Spark reads the whole walk in one request, each photo labelled with where it was taken, and says which parts of the field differ (`zone`) and what was sown or planted is coming up (`emerging`).
- **Checking hypotheses on the photos.** `fieldnotes expect` has the model write, before it sees any photo, what photos would show for each hypothesis about the land; every later `observe` answers `agrees`, `disagrees` or `cannot tell` per hypothesis, and the timeline shows the answers day by day.
- **Where to cut first.** For a plot left uncut for a year that now looks like abandoned farmland, `fieldnotes propose --cut` gives one place and one height to cut first, with the reason and what the next days' photos should show. One proposal was written (2026-10-29); it is not yet marked.
- **Photos and voice.** The phone's own recorder; Muse Voice Transcribe writes it down in the farmer's language; Muse Spark sorts it into what was done, what was seen, and verdicts on the AI's lines. Built and tested with mocked answers; no real recording has been through it as of 2026-11-05.
- **From your own AI.** `fieldnotes mcp` serves the tools (`fields`, `read`, `observe`, `say`, `mark`, `propose`, `timeline`, `site`, `note`) to Claude Code, Claude Desktop, Muse Code or any MCP client; `--http` for an AI on another machine in the house.
- **The phone app is the main entrance** (Flet; Send, Read, Nouns today; the whole command line is being brought into it, WP18). The command line and the MCP server are the same functions for scripts and for your own AI.
- **Records.** Plain Markdown with YAML front matter; what every file and line means is written in `docs/records.md`, so other programs and other AIs can read a farm folder. A phone app (Flet) sends photos and voice in and shows the SAM overlays and the lines to mark. `pip install fieldnotes-farm`.

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
- Demo video (3 minutes): （作者が記入）
- Package: `fieldnotes-farm` on PyPI, https://pypi.org/project/fieldnotes-farm/ (0.1.0 published 2026-11-04 from the GitHub Actions Trusted Publisher workflow)

## Licence

AGPL-3.0-or-later.
