# fieldnotes ユーザーマニュアル(日本語版)

英語版 [manual.md](manual.md) が本体。内容は同じ。

2026-11-03 時点のコード(`fieldnotes --help` と各サブコマンドのヘルプ、`src/fieldnotes/app.py`)から書いたもの。英語の全体説明は [README.md](../README.md)、記録ファイルの一行一行の意味は [records.md](records.md) にある。ここには「毎日どう使うか」だけを書く。

## 1. これは何か

畑を AI と一緒に読み、その読みを家の中に平文の記録として残す道具。農家がすることは、写真を撮ること、行に ✓ ✗ を付けること、打つ代わりに話すこと。どんなやり方の畑にも使え、アプリ自身の農法は無い。

- **SAM 3.1** が写真の中の作物・草・裸地を切り出し、被覆率(%)を出す。
- **Muse Spark** が写真を、前の日の記録と土地の公開データと照らして読み、行にして書く。
- **Muse Voice Transcribe** が畑で話した録音を文字にし、Spark が「したこと」「見たこと」「AI の行への ✓ ✗」に仕分ける。(配線はできている。2026-11-05 時点で実際の録音はまだ通していない。)

AI の書いた行はすべて「right(✓)」「wrong(✗)」と理由を付けられ、その訂正が次の読みに戻る。チャット画面はない。いつも使っている AI(Claude、ChatGPT、Muse Code など)から MCP でつなぐか、コマンドかスマホアプリを使う。記録は Markdown で、人も別の AI も読める。

## 2. 準備

### 2.1 インストール

リポジトリからそのまま使う場合(今の農家の PC の状態):

```bash
cd /home/dev/dev/fieldnotes
.venv/bin/fieldnotes --help
```

新しく入れる場合:

```bash
python -m venv .venv && .venv/bin/pip install -e ".[all]"
```

`[all]` にはスマホアプリ(Flet)と音声ファイルの変換(PyAV)が入る。`fieldnotes` コマンドが見つからないときは `.venv/bin/python -m fieldnotes ...` でも同じ。

`pip install fieldnotes-farm` で PyPI から入る(2026-11-04 公開)。extra は `[app,voice]`。

### 2.2 Meta のキー

dev.meta.ai で作った Model API のキーを、どちらかに置く。

- 環境変数 `MODEL_API_KEY`
- ファイル `~/.config/fieldnotes/model_api_key`(`fieldnotes` は**フォルダ**、その中の `model_api_key` が**ファイル**。権限は 600)

```bash
mkdir -p ~/.config/fieldnotes && chmod 700 ~/.config/fieldnotes
# キーを ~/.config/fieldnotes/model_api_key に書き、chmod 600 する
```

キーは呼び出すたびに読むので、置き直しても再起動はいらない。見つからないと `no Meta Model API key: set MODEL_API_KEY or write it to ...` と出る。

### 2.3 最初の設定(どれも引数なしで今の値を表示)

| コマンド | 意味 |
|---|---|
| `fieldnotes consent yes` / `no` | Muse Spark に送るものを Meta が学習に使ってよいか。アプリは初回起動時に同じことをダイアログで聞く(右上の歯車からいつでも変えられる) |
| `fieldnotes language ja` / `en` / `auto` | AI が書く言語。`auto`(既定)は使っている PC やスマホの言語 |
| `fieldnotes reader spark` / `glimmer` | 畑を読むモデル。`glimmer` は家の中の llama.cpp サーバー(既定 `http://192.168.100.6:11434/v1`、`--url` と `--model` で変更、`--check` で応答確認)。動画やふだんは `spark` |

## 3. 農場フォルダを作る

農場ひとつ = フォルダひとつ(`photos/` と `records/` を持つ)。コマンドはそのフォルダの中で実行するか、`--root DIR` を**サブコマンドの前**に付ける。既定は環境変数 `FIELDNOTES_ROOT`、なければ今いるフォルダ。

```bash
mkdir ~/farm/myfarm && cd ~/farm/myfarm
fieldnotes init --place "新居浜市 萩生" --country JP --lat 33.912172 --lon 133.264208 \
  --climate "warm temperate, humid" --method "元は水田。不耕起・無肥料・刈り敷きは前提ではない。農薬は使わない"
```

- `--method` は「この畑をどう作っているか」を自分の言葉で。これが毎回のプロンプトに入る。アプリ自身には既定の農法がない。省くと `site.md` に `method: not recorded yet` と書かれ、プロンプトにもそう入る。あとで `records/site.md` の `method:` 行を直せばよい。
- 二度目の `init` は既存の `site.md` を上書きしない(「もうあります」と出る)。

続けて土地の公開データを取る:

```bash
fieldnotes lookup                 # 標高・地質・土壌・活断層・ハザード・筆ポリゴン・地質図幅・近くの史跡 → records/lookup.md
fieldnotes search 城 --save       # 近くの名前を Wikipedia と OpenStreetMap で探し、lookup.md に足す
fieldnotes surroundings           # 畑のまわりの地図タイルを一度だけ読む(--force でやり直し)
```

自分の知っていることは `note` で `records/site.md` に入れる。行には必ず種類が付く。

```bash
fieldnotes note "棒は 20 cm くらいで止まる。抜くのに力がいる"                 # 自分の言葉 → record 行
fieldnotes note --source "石井町史 (1991) p.833" --section history "……"    # 文書の記述 → data 行(出典付き)
fieldnotes note --page 写真.jpg                                              # 文書のページ写真から、畑に関わる部分を読み手が書き写す
```

`--section` は `terrain` / `geology` / `history` / `works`、`--date` は言った日(既定は今日)。`hypothesis`(仮説)の行は前提ではなく「確かめること」として扱われる。

## 4. 毎日の使い方

### 4.1 畑を歩いて撮る

- 同じ経路を毎日歩き、スマホの**位置情報をオン**にして 20〜50 枚撮る。1 回の読みで送れるのは 50 枚まで。超えると分けて読んでからまとめる。
- 写真は撮影時刻順に `photos/<畑>/<日付>/` に並び、`index.json` に時刻・位置・向きが残る。
- 読みの中で写真は「3 of 42, 10:21, NW corner, facing W」と呼ばれる。位置の言葉(NW corner、middle、S edge など)は、写真の半分以上が入る**筆ポリゴン**を枠にして付く。半分に満たないときは歩いた範囲が枠になり、各写真に `in the parcel` か `outside the parcel, 35 m S`(区画の縁からの距離と方角)が付く。この場合の「S edge」は歩いた範囲の南端であって畑の南端ではない。区画外の写真だけで見えた zone には読み手が「outside the parcel」と距離を書くよう指示される。
- 畑のまわり(隣の畑、畦、川岸、放棄地)もときどき撮る。アプリでは「近所(畑のまわり)」を選ぶ。コマンドなら畑名 `_around` に送り、`fieldnotes observe _around` で読む(SAM は使わない)。家や人は撮らない。

### 4.2 スマホアプリ

PC で起動し、スマホのブラウザから開く(家の中のネットワーク限定。ログインはない)。

```bash
fieldnotes --root ~/farm/myfarm app --port 8550     # スマホで http://<PC のアドレス>:8550
```

下の 3 つのタブ:

| タブ | 何をする |
|---|---|
| **送る** | 畑と日付を選び「撮る・選んで送る」で写真を送る(新しい畑名もここで作れる)。「声を送る(したこと・見たこと)」でスマホの録音アプリのファイルを送る |
| **読む** | 畑と日付を選び「読む」で観察を実行(数分)。写真と SAM の重ね描きを見て、AI の各行を ✓ か ✗(理由入力)で判定。「声で答える(✓ ✗ と理由)」で声でも判定できる |
| **名詞** | SAM に探させる名詞句(「yellow flower clusters」など)と前回それが何%見つけたか。✓ ✗ と置き換えの名詞を付けられる |

右上: 文A ボタンで画面と AI の言語、歯車で学習同意の変更。ブラウザのマイクは HTTPS か localhost でしか使えないので、録音はスマホ標準の録音アプリで行い、そのファイル(m4a、3gp、ogg、webm、WAV)を送る。

PC のブラウザペインで開くと日本語が □ になることがあるが、これは描画側のフォントの問題で、スマホでは正常に出る。

### 4.3 コマンドで同じことをする

```bash
fieldnotes observe uncut 2026-11-03       # 天気 → SAM → Muse Spark → records/uncut/2026-11-03.md(+ overlay 画像)。日付省略で今日
fieldnotes show uncut                     # 最新の記録を表示(日付を付ければその日)
fieldnotes voice uncut memo.m4a 2026-11-03   # 録音を文字にし、work / seen / ✓✗ に仕分けて記録に入れる
fieldnotes mark uncut 2026-11-03 dominant right
fieldnotes mark uncut 2026-11-03 overall wrong "むらがある。一様ではない"
fieldnotes mark uncut 2026-11-03 zone#2 wrong "それは隣の田んぼ"     # 同じ key が複数あるときは #2, #3
fieldnotes concept uncut goldenrod wrong "オギも拾う" --replace "yellow flower clusters"
fieldnotes timeline uncut                 # 日ごとの一覧 + 表「出てきた種 × 日」「仮説 × 日」(--since 日付)
```

- `observe` を同じ日にもう一度走らせると AI の行は書き直されるが、✓ ✗ とメモは残る。文言が変わった判定済みの行は `## Earlier AI lines` の下に移る。
- AI の行の key: `overall`、`dominant`、`crops`、`acidity`、`fertility`、`dryness`、`zone`、`emerging`、`leaf_colour`、`weed_height`、`soil`、`animal`、`other`。農家の声からの行: `work`、`seen`。

### 4.4 提案と仮説の確認

```bash
fieldnotes propose uncut --cut                          # まずどこを何cmで刈るか → records/_proposals/uncut/<日付>-cut.md
fieldnotes propose uncut --seeds "クリムソンクローバー, ライムギ"   # 手元の種で緑肥の混播案
fieldnotes mark uncut 2026-11-03 height wrong "高すぎる" --proposal cut

fieldnotes expect uncut                                 # 写真を見る前に、site.md の各仮説が成り立つなら写真に何が写るかを書かせる → records/_checks/uncut/expect.md
fieldnotes mark uncut 2026-11-03 h3 wrong "写真では分からない" --proposal expect
fieldnotes compare                                      # 各畑の最新記録を並べて雑草バロメーターで比べる → records/_compare/<日付>.md
```

`expect` を一度書くと、その後の `observe` は毎回 `## Checks` を記録に足す(仮説ごとに `agrees` / `disagrees` / `cannot tell`)。種をまく前は `cannot tell` が正しい答えになることが多い。`timeline` の末尾の表で日ごとの答えが並ぶ。

## 5. 自分の AI からつなぐ(MCP)

写真と声はアプリから入れ、読みや判定はふだんの AI に頼む。

```bash
# Claude Code
claude mcp add fieldnotes -- /home/dev/dev/fieldnotes/.venv/bin/fieldnotes --root /home/dev/farm/rokuse mcp
```

Claude Desktop(`claude_desktop_config.json`):

```json
{"mcpServers": {"fieldnotes": {"command": "/home/dev/dev/fieldnotes/.venv/bin/fieldnotes",
                               "args": ["--root", "/home/dev/farm/rokuse", "mcp"]}}}
```

Muse Code(`~/.config/muse/settings.json`):

```json
{"schema_version": 1,
 "mcp_servers": {"fieldnotes": {"transport": "stdio", "command": "/home/dev/dev/fieldnotes/.venv/bin/fieldnotes",
                                "args": ["--root", "/home/dev/farm/rokuse", "mcp"], "mode": "optional"}}}
```

ツール: `fields`(畑一覧)、`read`(記録)、`observe`(数分かかる)、`say`(AI に話したことを原文のまま残し、work / seen / ✓✗ に仕分け)、`mark`(自分が言ったことだけ)、`propose`(`cut` か `cover_crop`)、`timeline`、`site`、`note`。`→ farmer: right/wrong` の付いた行だけが農家の判断で、付いていない行は AI の読みに過ぎない、とサーバーが AI に伝える。

別の機械の AI からは `fieldnotes mcp --http`(ポート 8551、`http://<PC>:8551/mcp`)。サインインはないので家の中だけで使う。

## 6. 記録の読み方

一行の形はどれも同じ:

```
- <key>: <本文> [0.85]  → farmer: right | wrong (理由)
```

`[0.85]` は AI の確信度(0〜1)。`→ farmer:` は `mark` が後から付けるもので、AI は書かない。付いていない行は未判定。

`records/site.md` の行は種類で始まる: `data`(出典付きの公開データや文書)、`record`(農家がした・見たこと)、`hypothesis`(未確認の読み)、`supported` / `refuted`(確かめたもの)。AI が写真から読んだことは `site.md` に入れない。入れると次の読みがそれを事実として繰り返す。

主なファイル(全部は [records.md](records.md)):

```
photos/<畑>/<日付>/                 写真、録音、index.json
records/<畑>/<日付>.md              その日の観察(AI の行、Checks、農家の声、✓✗)
records/<畑>/<日付>-overlay-<n>.jpg  SAM が見つけたものを写真 n に描いたもの
records/site.md                     土地について分かっていること・信じていること
records/lookup.md                   lookup の結果(出典付き)
records/_proposals/<畑>/            刈る・緑肥の提案
records/_checks/<畑>/expect.md      仮説ごとの「写真に何が写るはずか」
records/_concepts/<畑>.md           SAM に頼む名詞
records/_plants/<属_種>.md          優占草がなぜ優占するか(AI の読み)
```

`sample/` はこの形の実例(徳島の畑、日本語)。`sample-en/` は同じ写真を英語で読み直したもの。

## 7. 困ったとき

| 症状 | 対処 |
|---|---|
| `no Meta Model API key` | 2.2 のどちらかに置く。フォルダ名とファイル名を確認 |
| `fieldnotes: command not found` | `.venv/bin/fieldnotes` をフルパスで。または `.venv/bin/pip install -e .` |
| `fieldnotes app` や m4a の録音が extra を要求する | `.venv/bin/pip install -e ".[app,voice]"` |
| 読みの位置が畑と合わない(「S edge」が隣の段など) | 4.1 の通り、写真の半分以上が筆ポリゴンに入らないと歩いた範囲が枠になる。`in the parcel` / `outside the parcel, … m` の表記を見る。区画の中心から歩く |
| SAM の被覆率がほぼ 0 | 背の高い密な草、刈り株、黒マルチ、水面は今の名詞では拾えないことが多い。「名詞」タブか `concept --replace` で言い換えを試す。読みの `basis` 行に、どの数字が SAM のもので、どれが AI の目視かが書かれる |
| 写真を別のディスクから取り込めない(`Invalid cross-device link`) | 2026-11-03 のコードで直っている。古い版なら同じディスクに置いてから送る |
| 同じ日を読み直したい | `observe` をもう一度。✓ ✗ とメモは残る |
| AI が前の自分の読みを事実として繰り返す | `site.md` に AI の読みが入っていないか見る。`_plants/` のメモは AI の読み |
| スマホからアプリが開けない | PC と同じ Wi-Fi か、ポート 8550 が開いているか。アドレスは `http://<PC の IP>:8550` |

## 8. 言葉

- **畑(field)**: 農場の中の名前の付いた区画(`uncut`、`mix1`、`row1`、`main` など)。フォルダ名そのもの。
- **筆ポリゴン**: 農林水産省の農地区画データ。位置と形の参考情報で、境界や権利を示すものではない。
- **zone**: 畑の中で他と違う部分。`emerging`: まいた・植えたものが出てきたこと(自生や成株は含まない)。
- **Checks / h1, h2 …**: `site.md` の仮説の番号(並び順)と、その日の写真が仮説に対してどちらを向いたか。
