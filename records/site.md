---
site: ishii-takagawara
lat: 34.0801
lon: 134.4454
elevation_m: 7
checked: 2026-10-28
---

# Site profile

What is known or believed about the field. Every line is a claim with a
source and a status, so a reader (or a model) can tell data from belief:

- `data` — a public measurement or record, with its source.
- `record` — something the farmer did or saw (dates, actions). Not a theory.
- `hypothesis` — a reading of the field, by the farmer or by the AI, not yet checked.
- `supported` / `refuted` — checked; the evidence is named on the line.

Hypotheses are **not** given to the model as premises. They are things to
check, from outside sources and from this field's own records (see the end).
The farmer's knowledge and the AI's guesses are treated the same way.

## Location

- `data` 徳島県名西郡石井町 高川原 (municipality code 36341). — GSI reverse geocoder
- `data` Elevation 7 m (1 m LiDAR DEM). — GSI elevation API
- `data` Open-Meteo weather grid point used for the records: 34.0598 N, 134.4375 E, 5 m, about 2 km SSW of the field.
- `data` Nearest JMA station with temperature and rain: 徳島 (71106), 2 m, 12 km east. Not used; Open-Meteo is closer.

## Terrain

- `hypothesis` A slightly raised ground (微高地) on the south side of the Yoshino River plain. — farmer. Check: GSI 地形分類 (land condition map).
- `refuted` "Low floodplain" — AI guess from elevation alone; corrected by the farmer. Elevation cannot tell 微高地 from floodplain.
- `hypothesis` The soil was laid down by a great flood about 2000 years ago. The 高川原遺跡 records note a great flood 1800–2000 years ago (late Yayoi). — farmer. Not yet confirmed in the report text, which is not online. Check: archaeological / flood-history literature for the lower Yoshino.
- `hypothesis` Ordinary floods do not inundate it. — farmer. Check: MLIT flood hazard and past-inundation maps.
- `hypothesis` Underflow (伏流水) runs about 4 m below the surface. — farmer. Check: well records, groundwater surveys.
- `refuted` "High water table" — AI guess from the presence of ogi; the farmer puts the underflow at about 4 m.

## Geology

- `data` Surface geology at the field: unconsolidated deposit, mud (未固結堆積物「泥」). Landform: 扇状地性低地（氾濫原性低地）. Soil: 細粒灰色低地土壌 (gray lowland soil, fine). — 国土交通省 20万分の1土地分類基本調査 GIS data, 徳島県 (https://nlftp.mlit.go.jp/kokjo/tochimizu/F2/GIS/36.zip), point-in-polygon at 34.0801, 134.4454, checked 2026-10-28. At 1:200,000 a small rise (微高地) does not show; the landform unit does not contradict the farmer's 微高地 within it.

- `hypothesis` Regional context (general knowledge): the Yoshino valley follows the Median Tectonic Line; north of the river is the Izumi Group, south is the Sambagawa belt (crystalline schist). — AI. Check: GSJ seamless geology map (`https://gbank.gsj.jp/seamless/v2/api/1.0/legend.json?point=34.0801,134.4454`, under maintenance on 10-27 and 10-28).

## Soil

- `hypothesis` Formed from silt of black schist (黒色片岩, Sambagawa pelitic schist). — farmer. Check: NARO 日本土壌インベントリー (https://soil-inventory.rad.naro.go.jp/, read by hand), GSJ map.
- `hypothesis` Low in organic matter: mineral silt from one flood, then a well-drained raised ground where organic matter decomposes fast. — farmer. Check: measure soil organic matter.
- `hypothesis` Minerals are plentiful (black schist), but that only helps if the plants can take them up themselves. — farmer, 2026-10-28
- `hypothesis` Even among unfertilised fields, a soil rich in organic matter behaves differently from this one. — farmer, 2026-10-28
- `hypothesis` This difference shows mainly in nitrogen. Rock minerals carry almost no nitrogen, so in this low-organic-matter schist silt nitrogen has to come from organic matter built up by roots, or from legumes fixing it. In an organic-rich soil, humus releases nitrogen every season. Here P, K, Mg and Ca are in the rock and need roots and fungi to reach them. — AI (Claude), 2026-10-28. Check: leaf yellowing in crops and weeds, and how legumes do here.
- `hypothesis` In a field like this, letting ogi grow is not necessarily bad. — farmer, 2026-10-28
- `hypothesis` Ogi is hard to turn back into crop ground, but that may be the price of letting roots till the field instead of a machine. — farmer, 2026-10-28
- `hypothesis` Why ogi could help here. Its dense rhizomes and deep roots put organic matter into the soil itself, not only on the surface, and they open up silt that packs tight. As a grass it hosts mycorrhizal fungi. Some studies report nitrogen-fixing bacteria living with Miscanthus, though how much this adds in the field is unclear. The cost is that its rhizomes are hard to turn back into crop ground, and it shades and competes. So how and when to cut it matters more than whether to remove it. — AI (Claude), 2026-10-28. Check: literature on Miscanthus root biomass and associated N fixation; this field's own records after cutting.
- `hypothesis` What matters is organic matter in the soil (from roots), not above ground. — farmer. Check: literature on root-derived vs surface-residue soil carbon.
- `hypothesis` Black-schist silt does not suit vegetables with weak roots. — farmer. Check: see below.

## Surroundings

- Read from GSI maps (current and 1960s/1970s aerial photos, standard map, 治水地形分類図) into `records/surroundings.md`; each line there is a hypothesis for the farmer to mark.
- `hypothesis` 治水地形分類図 (lcmfc2): the field point falls in the light-green unit, which I read as 氾濫平野, about 50–100 m east of a 旧河道 band (blue stripes) along the winding river to the west. — AI (Claude) reading the map legend, 2026-10-28. Conflicts with the farmer's 微高地; the 1:25,000 map may not resolve a small rise. Check: the legend, and a 1 m DEM profile.
- `hypothesis` In the 1961–69 and 1974–78 aerial photos, the field lies at the edge of houses and trees by the river while paddies spread around them. Old settlements tend to sit on slightly raised ground, which would support 微高地. — AI (Claude), 2026-10-28
- `data` Spot elevations (GSI, mostly 1 m laser DEM), field 7.0 m; 75–500 m east 7.0–7.9 m; 150–300 m south 7.5–7.6 m; points 150 m west and 150 m north 5.3 m and 2.7 m (river / channel). A handful of points does not settle whether the field is a rise; a dense profile would. — GSI elevation API, 2026-10-28
- `hypothesis` The river right beside the field, with its banks, is a likely seed source for ogi and goldenrod. — AI (Claude), 2026-10-28
- `data` The winding river beside the field is the 飯尾川. It is an old main channel of the Yoshino River, with a very gentle bed slope, and it crosses the low land of the Yoshino's south-bank flood area. In the first improvement works (from 1932) the channel was widened up to 石井町高川原, and the sharp bends between 高川原村加茂野 and 南井上村 were cut off with a new channel. Since the Yoshino's levees were built (late Meiji to early Shōwa), it has been the prefecture's largest 内水 river. — MLIT 四国地方整備局「吉野川歴史探訪 その2 飯尾川河川改修のはじまり」 https://www.skr.mlit.go.jp/tokushima/kouhoushi/matome/rekishitanbou/PDF/r-48.pdf
- `hypothesis` Why it meanders. A small river now flows in a bed once cut by the much larger Yoshino. On flat land with a gentle slope and fine, cohesive silt banks, it has too little energy to run straight, so it bends. It also runs along the low ground between the Yoshino's natural levees and the southern hills. The bends next to the field are upstream of the 1932 cut-off, so they were left as they were. — AI (Claude), 2026-10-28
- `hypothesis` The field (red circle on the maps) is where the river's flow hits head-on in a flood, on the outer side of the bend. — farmer, 2026-10-28
- `refuted` "The flood flow built the raised ground". AI (Claude) guess; the farmer says the ground was a 微高地 from the start, as the 高川原遺跡 excavation records show.
- `refuted` "Coarse load (sand, coarse silt), well drained, sandy lenses". AI (Claude) guess from the flow hitting here. The farmer points out that black schist does not give coarse grains. — 2026-10-28
- `hypothesis` Grain size here is set by the source rock as much as by the flow. Black (pelitic) schist splits along its foliation into thin flakes, which weather to fine, platy silt and clay, not sand. So even where the flood hit hardest, the deposit is fine. Platy grains settle in flat layers and pack tightly. That fits silt that holds water (ogi), soil that may crust and harden when dry, and the farmer's 'not for weak-rooted vegetables'. It also fits a soil low in organic matter, being fresh mineral deposit. Flood water may have brought ogi rhizome pieces and seed. — AI (Claude), 2026-10-28
- `hypothesis` On this reading, the field's soil was laid by the old Yoshino main channel next to its bed. The raised ground was there before (excavation records, per the farmer); the flood laid fine schist silt on it. This fits the flood deposit, and it fits black-schist silt, since the Yoshino brings Sambagawa schist from upstream. The underflow about 4 m down may run in the sand and gravel of the old channel. — AI (Claude), 2026-10-28. Check: borehole logs (国土地盤情報検索サイト KuniJiban), well records.
- `hypothesis` The field lies on an original 微高地. The excavation records of the 高川原遺跡 show it. — farmer, 2026-10-28. Check: the reports below.
- `data` 高川原遺跡 (石井町). Finds include a dōtaku-shaped clay object and ink-inscribed haji ware. The periods given are Yayoi, ancient and medieval. Reports: 石井町 1979『徳島県高川原遺跡調査概報 銅鐸型土製品・墨書土師器出土遺跡』(NCID BB07298783), and 石井町教育委員会 1980『高川原遺跡発掘調査報告書』(NCID BB07298149). Also 松永住美・近藤賢 1982「徳島県高川原遺跡」『日本考古学年報』. The full texts are not online; nabunken lists them without files. — 奈良文化財研究所 全国遺跡報告総覧 https://sitereports.nabunken.go.jp/99707 , https://sitereports.nabunken.go.jp/99708
- Pending: what the farmer knows of the neighbours (what is grown next door, fertiliser or herbicide use, where water comes from, where animals come in).

## History

- Pending: GSI aerial photos (1940s onward) and old topographic maps for land use; town history (石井町史).

## Farming

- `record` Natural farming (Fukuoka method): no tillage, no fertiliser, no pesticide. Weeds are ground cover, not a target.
- `record` No fertiliser since 2023 (2026 is the fourth year). — farmer (year to confirm)
- `record` Spot 1: daikon (Raphanus sativus) and kailan (Brassica oleracea var. alboglabra), sown 2026-10-18, broadcast and mixed in the same strip, into cut-grass and straw mulch. 20 mm rain on 10-19 (Open-Meteo). Cotyledon to first true leaf on 10-27.
- `record` Spot 3: a plot left uncut for a year (autumn 2025 to autumn 2026, to confirm), now tall goldenrod (Solidago altissima) and ogi (Miscanthus sacchariflorus), above head height. Stands in for abandoned farmland. — farmer, photo 2026-10-28
- `record` Planned for autumn 2026: a mixed sowing led by rye, with crimson clover (Trifolium incarnatum) as the legume. — farmer, 2026-10-28
- `hypothesis` Hairy vetch is too strong in this farm's fields, so crimson clover is used instead. — farmer, 2026-10-28
- `refuted` "Susuki (Miscanthus sinensis)" — AI identification; corrected to ogi by the farmer.
- `data` Masanobu Fukuoka was born in 伊予郡南山崎村, now 伊予市 (石坂 2021, 愛媛大学, https://ehime-u.repo.nii.ac.jp/record/2001326/files/AA12777305_2021_50_1-20.pdf); a book biography gives 伊予市大平. The farm (福岡正信自然農園) is in 伊予市 (its official site, https://f-masanobu.jp/). No street address found.
- `data` Surface geology at 伊予市大平 (GSI address point 33.71682, 132.7052, the town's representative point, not the farm itself): consolidated sedimentary rock, alternating sandstone and shale (固結堆積物「砂岩・頁岩互層」). Landform: 小起伏山地. Soil: 黄色土壌. — 国土交通省 20万分の1土地分類基本調査 GIS data, 愛媛県 (https://nlftp.mlit.go.jp/kokjo/tochimizu/F2/GIS/38.zip), checked 2026-10-28.
- `data` Climate, 1991–2020 means. This field: 16.2 °C, 2021 mm a year, January 5.7 °C, August 27.4 °C. 伊予市大平: 15.5 °C, 1714 mm, January 5.1 °C, August 26.5 °C. Similar temperatures; about 300 mm more rain here. — Open-Meteo archive (ERA5), grid points 5 m and 131 m.
- `hypothesis` What this field shares with Fukuoka's 大平 is lying just south of the Median Tectonic Line. — farmer, 2026-10-28. In Tokushima the MTL fault zone runs along the southern edge of the Sanuki mountains, north of the Yoshino (地震調査研究推進本部 2017, above). This field is on the south bank.
- `hypothesis` This field's soil may also hold sandstone and shale from the north bank of the Yoshino. — farmer, 2026-10-28
- `hypothesis` In detail the geology differs, but both soils come from rocks of the Sambagawa belt. — farmer, 2026-10-28.
  - At 大平, the 1:200,000 map puts 緑色片岩 (green schist, a metamorphic unit) 1.3 km from the town's point. 安山岩質岩石 lies at 0.2 km, 砂岩・頁岩互層 at the point itself, and 礫岩・砂岩・頁岩（始新統） at 3.7 km. The farm's exact position is unknown. — MLIT 土地分類基本調査 愛媛県 GIS, 2026-10-28.
  - Here, the map gives only 泥 (mud). The farmer reads it as silt from black schist. Green and black schist are both crystalline schists of the kind the Sambagawa belt is made of.
  - 大平 lies south of the Median Tectonic Line. The MTL fault zone runs along the southern edge of the Matsuyama plain as the 伊予断層 (地震調査研究推進本部「中央構造線断層帯の長期評価（第二版）」2017, https://jishin.go.jp/main/chousa/katsudansou_pdf/20171219_mtl.pdf). Its trench sites are at 伊予市市場 (33.738, 132.698) and 三秋 (33.715, 132.680). 大平 (33.717, 132.705) is on the southeast side of the line through them. The farmer pointed this out on a map, 2026-10-28.
  - A 600 m grid over 大平 on the same MLIT map gives 砂岩・頁岩互層 in the north half and 緑色片岩 and 安山岩質岩石 in the south half (30 / 9 / 8 of 49 points).
  - Not yet checked against a map that names geological units (GSJ seamless map; under maintenance on 2026-10-28).

## How a hypothesis is checked

Mainly **from the weeds**. What grows here, how much, where, and how it changes
is the field's own answer about its soil, water and history. The daily photos
(SAM 3.1 cover per species, Muse Spark comparison, farmer's corrections) are the
instrument. Outside sources and trials come second. — farmer, 2026-10-28

1. **Weeds in this field.** Spark reads the weed record and says which weeds,
   in which places and seasons, would support or contradict the hypothesis.
   What a weed indicates is itself a claim and gets checked the same way.
2. **Outside sources.** Muse Spark with search grounding looks for evidence and
   answers `supports` / `contradicts` / `nothing found`, with citations. The
   farmer reads the citations; the status changes only when the farmer agrees.
3. **Trials.** Spark proposes what to try here that would tell
   the hypothesis apart from its alternatives, and the daily records answer it.

Example: "Black-schist silt does not suit vegetables with weak roots."

- First make it testable: which vegetables count as weak-rooted, and what does
  "does not suit" look like (poor germination, stunting, roots that stay shallow)?
- Outside: physical properties of pelitic-schist silt soils (crusting, hardening
  when dry, compaction) and root growth of the named vegetables in such soils.
- Weeds: which weeds grow, and how deep and dense their roots are, where the silt is thickest vs elsewhere.
- Trial: sow a weak-rooted and a strong-rooted vegetable side by side in the
  same strip, and compare survival and growth in the photos over the season.
