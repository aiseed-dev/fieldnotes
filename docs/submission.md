# Submission text (draft, 2026-11-03)

For the Meta Global AI Developer Hackathon form (Indie Developer track, theme *Build for Your World*). Written from the README and [story.md](story.md); nothing here is claimed that they do not say. Places marked （作者が選ぶ） are for the author to decide. Repository and video links are left blank.

## Project name

fieldnotes

## One-paragraph overview

fieldnotes reads a farmer's field together with AI and keeps the reading as plain-text records at home. Farming today runs on things bought from outside: fertiliser from suppliers, and the know-how to use it from the co-op and the dealers. Every field has different soil and different weeds, so no single method can be handed down from above. Instead, AI reads each field — its terrain, geology, weeds and weather — and the farmer looks, works, and checks the AI against what actually happens. The farmer only takes photos and talks. SAM 3.1 segments crops, weeds and bare soil; Muse Spark reads the photos against the previous days and against public data about the land; Muse Voice Transcribe writes down what the farmer says in the field. Every AI line can be marked right or wrong, and the corrections feed the next reading. There is no chat screen: the farmer connects from the AI they already use (Claude, ChatGPT, Muse Code ...) over MCP, and the records stay at home as Markdown that any person or model can read.

## What it does

- **Any farm, from one command.** `fieldnotes init` starts a farm folder with where it is. `fieldnotes lookup` fetches public data for the spot, each line with its source: elevation, bedrock, soil, history nearby; in Japan also the national sources (国土地理院 address, 1 m elevation and landform class, the nearest active fault, the hazard zones, the 筆ポリゴン farmland parcel, the 産総研 1:50,000 geological map sheet, the 農研機構 soil map). The farmer adds what they know with `fieldnotes note`, each line marked `data`, `record` or `hypothesis`.
- **The field from many photos.** The farmer walks the field with the phone's location on and takes 20–50 photos. SAM 3.1 segments each photo; Muse Spark reads the whole walk in one request, each photo labelled with where it was taken, and says which parts of the field differ (`zone`) and what was sown or planted is coming up (`emerging`).
- **Checking hypotheses on the photos.** `fieldnotes expect` has the model write, before it sees any photo, what photos would show for each hypothesis about the land; every later `observe` answers `agrees`, `disagrees` or `cannot tell` per hypothesis, and the timeline shows the answers day by day.
- **Where to cut first.** For a plot left uncut for a year that now looks like abandoned farmland, `fieldnotes propose --cut` gives one place and one height to cut first, with the reason and what the next days' photos should show. The farmer marks it right or wrong, then cuts.
- **Photos and voice, no typing.** The phone's own recorder; Muse Voice Transcribe writes it down in the farmer's language; Muse Spark sorts it into what was done, what was seen, and verdicts on the AI's lines.
- **From your own AI.** `fieldnotes mcp` serves the tools (`fields`, `read`, `observe`, `say`, `mark`, `propose`, `timeline`, `site`, `note`) to Claude Code, Claude Desktop, Muse Code or any MCP client; `--http` for an AI on another machine in the house.
- **Records.** Plain Markdown with YAML front matter; what every file and line means is written in `docs/records.md`, so other programs and other AIs can read a farm folder. A phone app (Flet) sends photos and voice in and shows the SAM overlays and the lines to mark. `pip install fieldnotes-farm`.

## Meta models and products used

| Model | Use |
|---|---|
| `sam-3.1` (Meta Model API) | segments crops, weeds, bare soil and the field's own noun phrases in every photo → cover % |
| `muse-spark-1.3` (Meta Model API) | reads the photos against the previous days and the site's public data, in the farmer's language; sorts what the farmer said; writes the cut proposal and the expectations per hypothesis |
| Muse Glimmer 30B (local, llama.cpp) | the same reading on a machine in the house, so photos need not leave it; chosen with `fieldnotes reader glimmer` |
| `muse-voice-transcribe-1.0` (Meta Model API) | the farmer's recordings, language-biased, with the field's plant names as keywords |

Muse Code: （作者が選ぶ — the README names Muse Code only for commits that carry the line `Written with Muse Code`; on 2026-11-03 no commit on `main` carries it, so the README does not claim it）

## Built during the hackathon

Everything in the repository was written during the event (26 Oct – 4 Nov 2026): the code under `src/fieldnotes/`, the scripts, the docs, and the sample farm's records under `sample/` (Japanese) and `sample-en/` (the same farm read in English). Two things existed before and are not used by the repository: a photo-alignment tool (`field-timelapse`) and a JMA-based weather site the author runs; the project's daily weather comes from the Open-Meteo archive.

## The field it was built on

The author's own field in Tokushima, Shikoku, just south of the Median Tectonic Line, where the author is testing Masanobu Fukuoka's natural farming (no tillage, no fertiliser, no pesticides). It has had no fertiliser for four years; one plot left uncut for a single year is now goldenrod and Amur silver grass (ogi) taller than a person. The tool reads such land and proposes where and how to cut first to bring it back into crops. What the records can show in the hackathon's days is the reading before the cut and the days after it; nothing more is claimed.

## Links

- Public repository: （作者が記入）
- Demo video (3 minutes): （作者が記入）
- Package: `fieldnotes-farm` on PyPI （作者が選ぶ: upload done or not）

## Licence

AGPL-3.0-or-later.
