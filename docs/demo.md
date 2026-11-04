# デモ動画（3 分半）の台本 — 2026-11-05 版、話す言葉も英語

2026-11-05 朝の差し替え（農家：「動画はすべて英語で作らないといけない」「台本の差し替えが必要」）。前の版（話すのは日本語、字幕は英語）はこの下に残さず、git の履歴にある。画面の文と数字は、11-05 の夜に一次資料で確かめた物と、`~/farm/video/fieldnotes-demo-provisional-2026-11-05.mp4` の各コマ（図 5 枚、Muse Spark の読み、英語の読み直しの記録）から取る。

守ること: 「枯渇 / depletion」と言わない（言うのは集中・依存・価格の跳ね）。uncut は「自分の畑を 1 年刈らずにおいて放棄地と同じ姿になった区画」と正直に言う。9 日で「復活」と言わない。できていない事はできていないと言う（音声の実録音はまだ、SAM の被覆はほぼ零、歩き撮りの行は未判定、歩いたのは 4 日）。AI は教える道具でなく、人と同じに間違う、と言う。数字は出所を名指しする。

## 台本

| 時間 | 画面 | 話すこと（英語） | 画面の文 |
|---|---|---|---|
| 0:00–0:20 | 徳島の畑を歩く。uncut 区画: 頭上のオギとセイタカアワダチソウ | This is my field in Tokushima, Japan. No fertiliser for four years. I left this plot uncut for one year, and now it looks like abandoned farmland. Grass and goldenrod taller than me, with nothing brought in. | My field. No fertiliser for four years. Uncut for one year: it looks like abandoned land |
| 0:20–0:55 | 図: 180 年の年表 → 世界の施肥 (FAOSTAT) → リン酸の輸出国・輸入国 → 埋蔵量 (USGS) → 価格 (世界銀行) | Fertiliser is the basis of industrial agriculture. For 180 years it has been bought from outside: guano, superphosphate, Haber-Bosch ammonia. Worldwide, fertiliser use per hectare rose nine-fold since 1961. Phosphate comes from a few countries: Morocco, Russia, China sell it; Brazil and India buy it. Sixty-eight percent of the reserves are in one country. Prices spiked in 2008 and 2022. This is not a Japanese problem. It is the baseline. | Fertiliser: the baseline of industrial agriculture, worldwide (FAOSTAT, USGS, World Bank) |
| 0:55–1:10 | 図: 土壌炭素のコマ | Soil carbon tells the same story. Agriculture has lost about 133 billion tonnes of carbon from the top two metres of soil, over twelve thousand years. Whether my field is losing or gaining, only a record over years can say. | Soil carbon: 133 Pg C lost to agriculture (Sanderman et al. 2017); what my field does, the record will show |
| 1:10–1:30 | 図: 仕組み（電話 → fieldnotes: SAM / Muse Spark / 記録 ← 自分の AI） | fieldnotes reads a field from the photos of a walk. SAM segments each photo. Muse Spark reads the walk as one field and writes plain-text lines. The records stay in my house. There is no chat of our own: I connect from the AI I already use, over MCP. Any farm, any country, any model that speaks the OpenAI format. | Specialist models do the work. The records stay at home. Your own AI reads them |
| 1:30–1:55 | 畑を歩いて撮る早回し（32 枚）→ SAM の重ね絵 → 記録の行（英語の読み直し） | I walk the field and shoot. Thirty-two photos, filed by time and GPS. SAM takes leaves, bare soil, plumes. Spark writes what is where, with the photo numbers and a confidence. Here it found the strip I cut that afternoon. | Walk and shoot. 32 photos read as one field: zones, with photo numbers and confidence |
| 1:55–2:20 | 記録の行に ✓ ✗ を付ける画面。「farmer: 0 ✓, 0 ✗ of 10 AI lines」。同じ写真の日本語と英語の読みが割れた行 | Every line waits for my mark: right or wrong, with a reason. An unmarked line is only the model's reading. AI must not become a tool that teaches you. AI makes mistakes, like people. Read the same photos twice and the model places the cut strip differently. That is why the farmer marks. | AI is not a teacher. It errs like a person. The farmer marks every line |
| 2:20–2:45 | site.md の土地のデータ（筆・標高・地質・土壌、出所つき）→ 仮説と Checks → timeline の表 | The land's public data goes into the reading: the parcel, a one-metre elevation model, the geology, the soil map, each line with its source. Hypotheses about the land, written before any photo, are checked against each day's photos: agrees, disagrees, cannot tell. The real check is by growing. | Primary data with the source on every line. Hypotheses checked day by day; the real check is by growing |
| 2:45–3:05 | 図: FAOSTAT の点線の所（2021 年の出所の変化） | Primary sources matter. But a primary source has its preconditions. This series drops twelve-fold in 2021. It is not a fall; the source changed. So primary sources must be cross-checked, and the chart says so. | A primary source has preconditions: cross-check it. FAOSTAT's 2021 break is a change of source, not a fall |
| 3:05–3:25 | install の画面、新居浜の畑の一枚、PyPI の頁 | Any farm starts from one command. A friend's field in Ehime was read the same way. The package is on PyPI; the records format is written down so other programs and other AIs can read a farm folder. What is not done yet: voice has not been used on a real recording; the SAM cover numbers are not right on this field; my lines are still unmarked. It is all in the repository. | pip install fieldnotes-farm. What is not done is written down too |
| 3:25–3:35 | 畑の全景 | Every farmer reads their own field, with the AI they already have — and marks what it got wrong. | Every farmer reads their own field, with the AI they already have, and marks what it got wrong |

数字の出所（話す物だけ）: 施肥の九倍 = FAOSTAT World N 8.6 → 71.3 kg/ha (1961 → 2024)、リン酸の輸出入 = FAOSTAT RFN 2022 国別、68 % = USGS MCS 2025（モロッコ・西サハラ 50 / 74 十億 t）、価格 = World Bank Pink Sheet、133 Pg C = Sanderman, Hengl & Fiske 2017 PNAS、FAOSTAT の断絶 = 同 CSV の flag（2020 年まで I/IFA、2021 年から A/日本の回答）。いずれも 2026-11-05 に自分で呼んで確かめた（implementation.md WP17）。

## 撮るもの（11-05 朝）

- 畑を歩く数秒と全景（英語の語りはこの上に）。
- 画面の録画は要らない: 図・記録・仕組みのコマは `~/farm/video/fieldnotes-demo-provisional-2026-11-05.mp4` から切り出せる（Pillow で描いたコマ、PNG は同じフォルダー）。
- 音声: 英語で話す。字幕は上の「画面の文」。

### 前の版の撮るもの（11-03 まで、参考）

| いつ | 何 |
|---|---|
| 10/29 | 新居浜の畑: 広い写真 2–3 枚/畑、まわり、声のメモ（日本語、m4a）。許可を取ってから |
| 10/30 朝 | uncut の刈る前: 全景と、提案が指す場所の寄り。`propose uncut --cut` の画面録画 |
| 10/30–31 | 刈る様子（手元と全景）。刈り敷きの寄り。混播の様子。声のメモ |
| 10/31– | 毎日、同じ道順で畑を歩いて撮る（位置情報オン、1 畑 20〜50 枚）。uncut と mix1。歩く様子を数秒、動画にも |
| 11/1–11/3 | 刈った後の定点から毎日 1 枚（杖を立てて）。何が先に戻るか、混播の芽 |
| 11/2 | 画面録画: 自分の AI から「uncut を読んで」「どこから刈る？」（録画は実行済みの記録を読む形でもよい）、timeline |
| 11/3 | 字幕を付けて編集。README に動画の URL |

## 使う素材の出典（話す数字）

- リン鉱石の埋蔵量とモロッコの割合、中国の輸出規制、耕作放棄地 42 万 ha: [story.md](story.md) 「根拠」節のとおり。新しい数字は入れない。

## 画面の文の確認（2026-11-03）

台本の画面欄のコマンド名・行の名前・ファイルの場所は、`.venv/bin/fieldnotes --help`（各サブコマンドも）、`fieldnotes --root sample timeline uncut` と `show uncut` の出力、`sample/records/_proposals/uncut/2026-10-29-cut.md`、`sample/records/_checks/uncut/expect.md` と突き合わせた。`sample/` にあるのは各畑 1 枚ずつの 10/27・10/28 の記録、10/29 の刈り方の提案、10/30 の expect で、歩いて撮った組（`zone` / `emerging`）の記録はまだ `sample/` にない（農家の自分の畑の記録は `~/farm/`、非公開）。モデルを呼ぶ画面（observe、propose、voice）は録画時の実行で出る。