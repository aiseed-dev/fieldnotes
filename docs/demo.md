# デモ動画（3 分）の台本と撮るもの

[design.md §6](design.md) の筋書きを、voice と刈り方の提案（WP8）と「自分の AI からつなぐ」（WP9a）、そして「畑を歩いて撮った多くの写真から判断する」（WP13、10/30 の方針）が入った形に更新したもの。畑の実験は多種の混植と混播。話すのは農家、日本語。英語の字幕は各段の *Caption* 行。撮影 11/3、提出 11/5 11:00 JST。

守ること（[story.md](story.md) の「注意」）: 「枯渇」と言わない（話の芯は偏在・輸出規制・輸入依存）。uncut は「放棄地と同じ姿になった区画」と正直に言う。9 日で「復活」とは言わない（見せるのは刈る前の読みと刈った後の数日）。大根・カイランは菌根菌と共生しないので、菌根の例にしない。販売は「次」と言うだけ（WP9b が入れば末尾に 15 秒）。

## 台本

| 時間 | 画面 | 話すこと | Caption |
|---|---|---|---|
| 0:00–0:25 | 徳島の畑を歩く。肥料袋と農協のチラシ（あれば）。uncut 区画: 頭上のオギとセイタカアワダチソウ | 肥料も、その使い方も、外から買っています。会社が情報システムを業者に預けてきたのと同じ形です。リン鉱石は 7 割がモロッコ、中国は輸出を絞っています。こちらは私の畑の一角。無肥料 4 年目、1 年刈らずにおいたら放棄地と同じ姿になりました。日本の耕作放棄地は約 42 万 ha、富山県ほどです | Fertiliser and the know-how both come from outside. This plot, left uncut for a year, now looks like abandoned farmland |
| 0:25–0:40 | 図 1 枚: 電話の写真と声 → fieldnotes（SAM / Muse Spark または自宅の Glimmer / Muse Voice Transcribe）→ 手元のテキストの記録 ← 自分の AI（MCP） | fieldnotes は畑を読む裏方です。切り分けは SAM、読みは Muse Spark か自宅の Glimmer、聞き取りは Muse Voice Transcribe。記録は手元のテキスト。私はいつも使っている AI からつなぎます。チャットは作っていません | Specialist models do the work. You keep the AI you already use; the records stay at home as plain text |
| 0:40–1:10 | 畑を歩いて電話で撮る（30 枚、数秒の早回し）→ 画面録画: 自分の AI で「uncut をきょう読んで」→ SAM のオーバーレイが並ぶ、記録の行（overall / dominant / zone / emerging）、地図に写真の点 | 畑を歩いて撮るだけです。30 枚を一組として読みます。SAM が 1 枚ずつ草と裸地を切り分け、Spark が畑全体の様子と、どこがどうなっているかを場所ごとに書きます。土地の背景（段丘か氾濫平野か、土の種類、区画）は国の一次データから読みに入っています | Walk and shoot. Thirty photos read as one field: SAM segments each, Muse Spark says what is where, with the land's primary data behind it |
| 1:10–1:40 | 画面録画: 「どこから刈る？」→ 刈り方の提案（summary / basis / where / height / leave / watch）。切り替わって畑: 提案の場所を刈る。刈り敷き | 「どこから刈ればいい？」。最初に刈る場所と高さを一つ、理由つきで出します。根は抜かず、刈って敷く。提案に ✓ か ✗ を付けて、刈りました | "Where do I cut first?" One place, one height, the reason. Cut and lay, roots left. The farmer marks it right or wrong, then cuts |
| 1:40–2:10 | 畑で電話の録音アプリに話す → アプリの 読む 画面: 文字起こし、work / seen の行、AI の行に付いた ✓ ✗ | 畑では話すだけです。「東側を刈って敷いた。ダイコンに本葉が出た。酸度の読みは違う、スギナが少ない」。文字になり、したこと・見たこと・AI への正誤に仕分けられて記録に入ります。訂正は次の読みに戻ります | In the field I only talk. It is written down and sorted into work done, things seen, and verdicts on the AI's lines. Corrections feed the next reading |
| 2:10–2:40 | 画面録画: `fieldnotes map`（空中写真に区画と、歩いた写真の点が色づき）と `fieldnotes timeline uncut`（日付 × 写真・overall・zone・emerging・したこと・✓✗）。刈った帯に混播した種が出てくる数日。新居浜の畑を `fieldnotes init` から同じ手順で読んだ画面を 5 秒 | 刈った帯にライムギとクリムソンクローバーを混播し、隣の区画は多種の混植。毎日歩いて撮ると、何をしたら、どこがどう変わったかが地図と日付で並びます。復活はこれから何年もかかる話で、見せられるのはこの数日です。同じ道具で、別の土地（愛媛・新居浜）も `init` から読めます | The cut strip sown with a mix, the next plot mixed planting. Walk daily, and the map and the timeline show what was done and what changed where. Any farm starts from `fieldnotes init` |
| 2:40–2:55 | （WP9b が入れば）買い手の AI が読み取り専用でつなぎ「肥料は本当に使っていない？」→ ✓ の行と出典。入らなければ: 記録ファイルを 1 つ見せる | （9b あり）買い手の AI がこの記録を読み、私が確かめた行だけを事実として受け取ります。（9b なし）売ることは次の課題です。この記録が、買い手に見せる根拠になります | The records become what a buyer's AI can check — the next step |
| 2:55–3:00 | 畑の全景 | 農家一人一人が、業者や指導を通さずに、自分の畑を読めるように | Every farmer reads their own field, with the AI they already have |

## 撮るもの（日付つき）

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
