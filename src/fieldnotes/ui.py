"""The words on the screen and in the CLI, in Japanese and English.

The screen follows the language the AI writes in (llm.language): Japanese
when that is Japanese, else English, the only two written so far. Each entry
is (Japanese, English); `{name}` fields are filled by Words.
"""

from __future__ import annotations

from . import llm

SCREEN = ("ja", "en")

TEXTS: dict[str, tuple[str, str]] = {
    # navigation and the app bar
    "nav.send": ("送る", "Send"),
    "nav.read": ("読む", "Read"),
    "nav.nouns": ("名詞", "Nouns"),
    "nav.land": ("土地", "Land"),
    "tip.language": ("言語", "Language"),
    "tip.capture": ("この画面を 1280×720 の PNG に（動画用）", "This screen as a 1280×720 PNG (for the video)"),
    "capture.saved": ("保存しました: {path}", "Saved: {path}"),
    "capture.failed": ("画面を保存できませんでした: {e}", "Could not capture the screen: {e}"),
    "tip.reader": ("読む AI", "Reading AI"),
    "tip.consent": ("AI の学習への利用", "Use for AI training"),
    "cancel": ("やめる", "Cancel"),
    "save": ("保存", "Save"),
    "close": ("閉じる", "Close"),
    "right": ("✓ 合っている", "✓ Right"),
    "wrong": ("✗ 違う", "✗ Wrong"),
    "wrong_title": ("{what}：違う", "{what}: wrong"),
    "what_wrong": ("どこが違いますか（書かなくてもいい）", "What is wrong? (optional)"),
    "not_saved": ("保存できませんでした: {e}", "Could not save: {e}"),
    "field": ("畑", "Field"),
    # 送る
    "send.title": ("畑の写真を送る", "Send photos of a field"),
    "send.new_field": ("＋ 新しい畑", "+ New field"),
    "send.new_field_name": ("新しい畑の名前（英小文字・数字・ハイフン）", "Name of the new field (a-z, 0-9, hyphens)"),
    "send.day": ("日付（写真に撮影日があればそちらを使う）", "Date (a photo's own date wins if it has one)"),
    "send.button": ("撮る・選んで送る", "Take or choose, and send"),
    "send.failed": ("送信に失敗: {name}: {error}", "Upload failed: {name}: {error}"),
    "send.placed": ("{n} 枚を {field} に置きました", "Filed under {field}: {n} photo(s)"),
    "send.bad_field": ("畑の名前を確かめてください（英小文字・数字・ハイフン）", "Check the field name (a-z, 0-9, hyphens)"),
    "send.bad_day": ("日付は 2026-10-28 の形で", "Write the date like 2026-10-28"),
    "send.sending": ("{n} 枚を送っています…", "Sending {n} photo(s)…"),
    "send.left": ("まだ届いていない {n} 枚: {names}", "{n} not yet uploaded: {names}"),
    "around": ("近所（畑のまわり）", "Neighbourhood (around the fields)"),
    # the walk strip
    "walk.none": ("この日の写真はまだありません", "No photos for this day yet"),
    "walk.count": ("写真 {n} 枚、GPS つき {gps} 枚（{note}）", "{n} photo(s), {gps} with GPS ({note})"),
    "walk.parcel": ("筆ポリゴンの上に", "on the parcel outline"),
    "walk.extent": ("歩いた範囲に", "on the walk's extent"),
    "walk.no_gps": ("位置は写真にありません。歩いた順だけ", "no location in the photos; walk order only"),
    # 読む
    "voice.button": ("声を送る（したこと・見たこと）", "Send your voice (what you did and saw)"),
    "voice.answer": ("声で答える（✓ ✗ と理由）", "Answer by voice (✓ ✗ and why)"),
    "voice.sending": ("声を送っています…", "Sending your voice…"),
    "voice.working": ("文字にして整理しています… {s} 秒", "Writing it down and sorting it… {s} s"),
    "voice.done": ("聞き取りました: {text}", "Heard: {text}"),
    "voice.sorted": ("記録に入れたもの: {n} 件", "Put into the record: {n}"),
    "voice.failed": ("声を記録できませんでした: {e}", "Could not record your voice: {e}"),
    "voice.heading": ("農家の声から（AI が整理）　合っていますか？", "From your voice (sorted by AI): is it right?"),
    "key.work": ("したこと", "Work done"),
    "key.seen": ("見たこと", "Seen"),
    "voice.words": ("大根, カイラン, 子葉, 本葉, 刈り草, 草マルチ, 刈り敷き, 足跡, 鹿, 猪, オギ, セイタカアワダチソウ, "
                    "クリムソンクローバー, ライ麦, 不耕起, 無肥料",
                    "daikon, kailan, cotyledon, true leaf, cut grass, grass mulch, footprints, deer, boar, "
                    "silvergrass, goldenrod, crimson clover, rye, no-till, no fertiliser"),
    "cli.heard": ("聞き取り: {text}", "Heard: {text}"),
    "read.title": ("畑を読む", "Read a field"),
    "read.day": ("日付（写真がある日）", "Date (days with photos)"),
    "read.button": ("読む", "Read"),
    "read.done_mark": ("読み済み", "read"),
    "read.no_photos": ("写真がまだありません。「送る」から送ってください。", "No photos yet. Send some from Send."),
    "read.photo": ("写真", "Photo"),
    "read.tap": ("タップで大きく", "Tap to enlarge"),
    "read.with_sam": ("SAM の色つき", "coloured by SAM"),
    "read.not_yet": ("まだ読んでいません", "not read yet"),
    "read.photos": ("写真 {n} 枚（{note}）　タップで大きく", "{n} photo(s), {note}. Tap to enlarge"),
    "read.bad_record": ("記録を読めません: {e}", "Cannot open the record: {e}"),
    "read.question": ("AI の読み　合っていますか？", "The AI's reading: is it right?"),
    "read.checks": ("仮説の確認　合っていますか？", "The hypotheses checked on the photos: is it right?"),
    "read.count": ("今日の印: ✓ {right}、✗ {wrong}（AI の {total} 行のうち）", "Marked today: {right} ✓, {wrong} ✗ of {total} AI lines"),
    "read.by": ("{model}、{date} の読み", "a reading by {model}, {date}"),
    "read.from": ("{label} の読み", "reading in {label}"),
    "read.earlier": ("読み直す前の行", "lines a re-run replaced"),
    "read.only_here": ("この読みにない行", "not in this reading"),
    "src.given": ("渡したもの: {list}", "Given: {list}"),
    "src.photos": ("写真 {n} 枚", "{n} photo(s)"),
    "src.sam": ("SAM の割合（名詞 {n}）", "SAM cover ({n} nouns)"),
    "src.weather": ("天気（Open-Meteo）", "weather (Open-Meteo)"),
    "src.earlier": ("前の {n} 日（✗ {wrong}）", "{n} earlier day(s) ({wrong} ✗)"),
    "state.no_lines": ("この読みには行がありません（AI は何も書きませんでした）", "This reading has no lines: the AI wrote nothing"),
    "state.no_sam": ("SAM の割合はこの記録にありません", "No SAM cover in this record"),
    "state.sam_nothing": ("SAM はこの名詞では何も見つけませんでした: {prompts}", "SAM found nothing for these prompts: {prompts}"),
    "state.no_checks": ("この日の写真では仮説を確かめていません", "The hypotheses were not checked on this day's photos"),
    "state.voice_not_heard": ("声は文字になっていません: {name}", "Voice not transcribed: {name}"),
    "state.no_reading": ("まだ読んでいません。「読む」を押すと AI が読みます。", "No reading yet. Press Read and the AI reads the day."),
    "read.empty": ("（まだ何も書かれていません）", "(nothing written yet)"),
    "read.note": ("農家のメモ", "Farmer's note"),
    "read.confidence": ("自信 {c}", "confidence {c}"),
    "read.reason": ("理由: {r}", "Why: {r}"),
    "read.running": ("読んでいます… {s} 秒（数分かかることがあります）", "Reading… {s} s (it can take a few minutes)"),
    "read.finished": ("読み終わりました（{s} 秒）。下の読みに ✓ ✗ をつけてください。",
                      "Done ({s} s). Mark each line below ✓ or ✗."),
    "read.failed": ("読めませんでした: {e}", "Could not read: {e}"),
    # 名詞
    "nouns.title": ("SAM に頼む名詞", "Nouns for SAM"),
    "nouns.help": ("SAM は名詞で探します。見つからない・違うものを探しているときは ✗ で直します。",
                   "SAM looks for things by noun. When a noun finds nothing or the wrong thing, mark it ✗ and give a better one."),
    "nouns.none": ("畑がまだありません。「送る」から写真を送ってください。", "No fields yet. Send photos from Send."),
    "nouns.target": ("探す相手: {t}", "Looks for: {t}"),
    "nouns.last": ("{by}　前回: {last}", "{by}. Last time: {last}"),
    "nouns.unused": ("✗ 使わない", "✗ Not used"),
    "nouns.replacement": ("かわりの名詞（英語・なくてもいい）", "Noun to use instead (English, optional)"),
    "nouns.hint": ("例: reed", "e.g. reed"),
    "by.ai": ("AI が考えた", "Suggested by the AI"),
    "by.farmer": ("農家が決めた", "Set by the farmer"),
    "by.shared": ("みんなの共有から", "From the shared list"),
    "by.default": ("最初から入っている", "Built in"),
    "last.never": ("まだ使っていない", "not used yet"),
    "last.no_match": ("見つからず", "no match"),
    "last.objects": ("個", "objects"),
    # 土地
    "land.title": ("土地と基準線", "The land and the baseline"),
    "land.help": ("data は出典のある公開データ、record は農家の言葉、hypothesis はまだ確かめていない読みです。",
                  "data is public data with its source, record is the farmer's words, hypothesis is a reading not yet checked."),
    "land.all": ("全部 {n}", "All {n}"),
    "land.status.data": ("data 公開データ", "data"),
    "land.status.record": ("record 農家の言葉", "record: the farmer's words"),
    "land.status.hypothesis": ("hypothesis 仮説", "hypothesis"),
    "land.status.supported": ("supported 確かめられた", "supported"),
    "land.status.refuted": ("refuted 否定された", "refuted"),
    "land.status.reference": ("reference 参考", "reference"),
    "land.site": ("この土地について（site.md）", "About this land (site.md)"),
    "land.lookup": ("公開データ（lookup.md、{fetched} に取得）", "Public data (lookup.md, fetched {fetched})"),
    "land.no_site": ("site.md がありません。この土地について、まだ何も書かれていません。", "No site.md: nothing is written about this land yet."),
    "land.no_lookup": ("lookup.md がありません。公開データはまだ調べていません。", "No lookup.md: the public data has not been looked up yet."),
    "land.section_empty": ("（まだ何も書かれていません）", "(nothing written yet)"),
    "land.check": ("確かめ方: {check}", "How to check: {check}"),
    "land.no_source": ("出典は書かれていません", "no source written"),
    "land.no_check": ("まだ写真で確かめていません（expect.md に入っていない行）", "Not checked on photos yet (not in any field's expect.md)"),
    "land.not_in_photos": ("{field} {id}: 写真には写らない、と expect.md にあります", "{field} {id}: expect.md says a photo cannot show this"),
    "land.not_checked_yet": ("{field} {id}: まだ確かめた日がありません", "{field} {id}: no day has checked it yet"),
    "land.by_day": ("{field} {id}: {days}", "{field} {id}: {days}"),
    "land.table": ("仮説を日ごとに", "Hypotheses day by day"),
    "land.table_help": ("写真が仮説の期待にどちらを指したか（モデルの読み）と農家の印です。タップで全文。",
                        "Which way the photos pointed for each expectation (a model's reading), with the farmer's mark. Tap for the whole line."),
    "land.table_none": ("{field}: 仮説を確かめた日はまだありません", "{field}: no day has checked a hypothesis yet"),
    "land.table_no_field": ("仮説の期待（expect.md）を書いた畑はまだありません", "No field has expectations (expect.md) yet"),
    "land.table_by": ("読んだモデル: {list}", "Read by: {list}"),
    "land.table_head": ("仮説", "Hypothesis"),
    "land.whole_file": ("{name} をそのまま見る", "{name} as it is"),
    "land.baseline": ("肥料と土壌炭素の基準線", "Fertiliser and soil carbon: the baseline"),
    "land.baseline_not_yet": ("まだありません。この国と世界の肥料・土壌炭素の行と図は、後の作業（WP17）で入ります。",
                              "Not yet. The fertiliser and soil-carbon lines and charts, this country beside the world, come with later work (WP17)."),
    "tools.title": ("コマンドの仕事", "The command line's work"),
    "tools.init": ("この土地を始める（site.md を作る）", "Start this land (write site.md)"),
    "tools.place": ("場所の名前", "Place name"),
    "tools.country": ("国コード（2 文字、JP など）", "Country code (two letters, e.g. JP)"),
    "tools.lat": ("緯度", "Latitude"),
    "tools.lon": ("経度", "Longitude"),
    "tools.climate": ("気候（任意）", "Climate (optional)"),
    "tools.method": ("やり方（任意、あなたの言葉で）", "How it is farmed (optional, your words)"),
    "tools.create": ("site.md を作る", "Write site.md"),
    "tools.note": ("知っていることを書き足す（site.md）", "Add what you know (site.md)"),
    "tools.note_text": ("書くこと", "What to note"),
    "tools.note_source": ("出典（文書なら。あなたの言葉なら空のまま）", "Source (for a document; empty for your own words)"),
    "tools.section": ("節", "Section"),
    "tools.save_note": ("書き足す", "Add"),
    "tools.field_work": ("畑ごと", "By field"),
    "tools.no_fields": ("写真か記録のある畑はまだありません", "No field has photos or records yet"),
    "tools.timeline": ("日ごとの記録（timeline）", "Day by day (timeline)"),
    "tools.expect": ("仮説の期待を書く（expect.md、AI）", "Write the expectations (expect.md, AI)"),
    "tools.propose_cut": ("刈り方の提案（AI）", "Propose a cut (AI)"),
    "tools.propose_cover": ("緑肥の提案（AI）", "Propose cover crops (AI)"),
    "tools.seeds": ("手元の種（カンマ区切り、任意）", "Seeds on hand (comma separated, optional)"),
    "tools.running": ("{what}… {s} 秒", "{what}… {s} s"),
    "tools.saved": ("保存しました: {path}", "Saved: {path}"),
    "tools.failed": ("できませんでした: {e}", "Could not do it: {e}"),
    "tools.reading": ("{model} の読み（{date}）。確かめるまでは読みです。", "A reading by {model} ({date}); a reading until checked."),
    "land.front.place": ("場所", "Place"),
    "land.front.country": ("国", "Country"),
    "land.front.lat": ("緯度", "Latitude"),
    "land.front.lon": ("経度", "Longitude"),
    "land.front.climate": ("気候", "Climate"),
    "land.front.method": ("やり方（農家の言葉）", "How it is farmed (the farmer's words)"),
    "land.front.elevation_m": ("標高 m", "Elevation m"),
    "land.front.checked": ("確かめた日", "Checked"),
    "land.front.site": ("名前", "Name"),
    "check.agrees": ("合う", "agrees"),
    "check.disagrees": ("合わない", "disagrees"),
    "check.cannot_tell": ("わからない", "cannot tell"),
    # AI の学習への利用
    "consent.title": ("AI の学習への利用", "Use for AI training"),
    "consent.text": (
        "畑の写真と記録は、読み取りのために Meta の AI（Muse Spark）に送られます。\n\n"
        "同意すると、送った写真と記録を Meta が AI の学習に使うことがあります。"
        "自然農の畑を AI が学べば、次に使う人の読みもよくなります。費用も安いモデルで済みます（おすすめ）。\n"
        "同意しない場合は、学習に使われない標準のモデルを使います（費用は少し高くなります）。\n\n"
        "あとから右上の歯車でいつでも変えられます。",
        "Photos and records of your fields are sent to Meta's AI (Muse Spark) to be read.\n\n"
        "If you agree, Meta may use what you send to train its AI. The more natural-farming fields "
        "the AI learns from, the better it reads them for the next farmer, and a cheaper model is used (recommended).\n"
        "If you do not agree, the standard model is used, which is not trained on what you send (it costs a little more).\n\n"
        "You can change this at any time with the gear at the top right."),
    "consent.now": ("今の設定: {state}", "Now: {state}"),
    "consent.agreed": ("同意している", "agreed"),
    "consent.refused": ("同意していない", "not agreed"),
    "consent.agree": ("同意する", "Agree"),
    "consent.refuse": ("同意しない", "Do not agree"),
    "consent.saved_yes": ("学習に使ってもらう設定にしました", "What you send may now be used for training"),
    "consent.saved_no": ("学習に使われない設定にしました", "What you send will not be used for training"),
    # 言語
    "lang.title": ("言語", "Language"),
    "lang.label": ("言語", "Language"),
    "lang.help": ("AI が読みや提案を書く言語です。画面もこれに合わせます（日本語のほかは英語）。"
                  "自動にすると、読ませたスマホや PC の言語になります。",
                  "The language the AI writes its readings and proposals in. The screen follows it "
                  "(Japanese, or else English). Auto uses the language of the phone or PC in use."),
    "lang.auto": ("自動（この端末: {lang}）", "Auto (this device: {lang})"),
    "lang.unknown": ("わかりません", "unknown"),
    "lang.saved": ("言語: {lang}", "Language: {lang}"),
    "lang.saved_auto": ("自動（それぞれの端末の言語）", "auto (each device's own)"),
    # 読む AI
    "reader.title": ("読む AI", "Reading AI"),
    "reader.help": ("SAM はいつも Meta の API を使います。ここで選ぶのは、畑を読む AI です。",
                    "SAM always runs on Meta's API. This chooses the AI that reads the fields."),
    "reader.spark": ("Muse Spark（api.meta.ai）", "Muse Spark (api.meta.ai)"),
    "reader.glimmer": ("Muse Glimmer（自宅のマシン）", "Muse Glimmer (a machine in the house)"),
    "reader.next": ("次の読み: {name}（{kind}）、{lang}で書きます", "Next reading by {name} ({kind}), written in {lang}"),
    "reader.auto_lang": ("（この端末の言語）", "(this device's language)"),
    "reader.url": ("Glimmer の接続先", "Glimmer server"),
    "reader.model": ("Glimmer のモデル名", "Glimmer model name"),
    "reader.test": ("Glimmer につながるか試す", "Test the Glimmer server"),
    "reader.checking": ("確かめています…", "Checking…"),
    "reader.ok": ("つながりました: {names}", "Connected: {names}"),
    "reader.ng": ("つながりません（{e}）", "Not reachable ({e})"),
    "reader.saved": ("読む AI: {name}", "Reading AI: {name}"),
    # what the AI reads, as the record's line titles
    "key.overall": ("畑全体", "Whole field"),
    "key.dominant": ("優勢な草", "Dominant plants"),
    "key.crops": ("野菜", "Crops"),
    "key.acidity": ("酸度", "Acidity"),
    "key.fertility": ("肥沃さ", "Fertility"),
    "key.dryness": ("乾き", "Dryness"),
    "key.leaf_colour": ("葉の色", "Leaf colour"),
    "key.weed_height": ("草の高さ", "Plant height"),
    "key.soil": ("土", "Soil"),
    "key.animal": ("動物", "Animals"),
    "key.other": ("その他", "Other"),
    "key.land_use": ("土地の使われ方", "Land use"),
    "key.neighbours": ("近所の様子", "Neighbours"),
    "key.water": ("水", "Water"),
    "key.seed_source": ("種の出どころ", "Seed sources"),
    "key.animals": ("動物", "Animals"),
    "key.history": ("昔の使われ方", "Past use"),
    # SAM's built-in nouns (concepts.BASE): what each looks for
    "base.leaf": ("葉（作物も草も）", "leaves (crops and weeds)"),
    "base.flower": ("花の房", "flower clusters"),
    "base.soil": ("裸地", "bare soil"),
    # pipeline steps, shown while a reading runs
    "step.around": ("近所の写真を読んでいます", "Reading the neighbourhood photos"),
    "step.weather": ("天気を調べています", "Looking up the weather"),
    "step.no_weather": ("天気は取れませんでした（{e}）", "No weather for the day ({e})"),
    "step.nouns": ("SAM に聞く名詞を用意しています", "Choosing the nouns for SAM"),
    "step.segment": ("SAM で {n} 枚を分けています", "SAM is segmenting {n} photo(s)"),
    "need.extra": ("この機能には追加のパッケージが要ります: pip install 'fieldnotes-farm[{extra}]'",
                   "This needs an extra: pip install 'fieldnotes-farm[{extra}]'"),
    "step.photo": ("SAM {n}/{of}: {name}", "SAM {n}/{of}: {name}"),
    "step.read": ("{model} が畑を読んでいます", "{model} is reading the field"),
    "step.check": ("{model} が仮説の期待と写真を突き合わせています", "{model} is checking the photos against the expectations"),
    "step.no_check": ("仮説の確認はできませんでした（{e}）", "No hypothesis check today ({e})"),
    "step.next": ("次回の SAM の名詞を用意しています", "Choosing SAM's nouns for next time"),
    "step.save": ("記録を保存しています", "Saving the record"),
    # CLI
    "cli.bad_date": ("日付は YYYY-MM-DD で: {text}", "Dates are YYYY-MM-DD: {text}"),
    "cli.no_record": ("{field} の記録がありません。先に fieldnotes observe {field}",
                      "No record for {field}. Run fieldnotes observe {field} first"),
    "cli.exists": ("{path} はもうあります。書き換えるなら手で編集してください", "{path} already exists. Edit it by hand to change it"),
    "cli.bad_place": ("--country は2文字、--lat は -90〜90、--lon は -180〜180 です",
                      "--country is two letters, --lat is -90 to 90, --lon is -180 to 180"),
    "cli.created": ("作りました: {path}。畑ごとの写真は photos/<畑>/<日付>/ に入れて、fieldnotes observe <畑>",
                    "Created {path}. Put each field's photos in photos/<field>/<date>/, then fieldnotes observe <field>"),
    "cli.saved": ("保存しました: {path}", "Saved: {path}"),
    "cli.already": ("すでに読んであります: {path}（やり直すなら --force。印は消えます）",
                    "Already read: {path} (--force to redo; the marks are lost)"),
    "cli.looking_up": ("公開データを調べています（標高、地質、土壌、近くの歴史）",
                       "Looking up open data (elevation, geology, soil, nearby history)"),
    "cli.nothing": ("見つかりませんでした", "Nothing found"),
    "cli.appended": ("追記しました: {path}", "Added to {path}"),
    "cli.consent_none": ("まだ決めていません（標準のモデルを使います）", "not decided yet (the standard model is used)"),
    "cli.consent_yes": ("同意しています（安いモデル。送ったものが学習に使われることがあります）",
                        "agreed (the cheaper model; what is sent may be used for training)"),
    "cli.consent_no": ("同意していません（標準のモデル。学習に使われません）",
                       "not agreed (the standard model; not used for training)"),
    "cli.consent": ("AI の学習への利用: {state}\nモデル: {model}", "Use for AI training: {state}\nModel: {model}"),
    "cli.lang_auto": ("言語: 自動（それぞれのスマホや PC の言語。この PC では {lang}）",
                      "Language: auto (each phone's or PC's own; on this PC {lang})"),
    "cli.lang_fixed": ("言語: {lang}（どの端末でも）", "Language: {lang} (on every device)"),
    "cli.reader": ("読む AI: {name}\nモデル: {model}", "Reading AI: {name}\nModel: {model}"),
    "cli.reader_glimmer": ("読む AI: {name}\n接続先: {url}\nモデル: {model}", "Reading AI: {name}\nServer: {url}\nModel: {model}"),
    "cli.glimmer_setting": ("（Glimmer の設定: {url}、{model}）", "(Glimmer settings: {url}, {model})"),
    "cli.error": ("エラー: {e}", "Error: {e}"),
}


def screen_language(lang: str | None) -> str:
    """The screen's language for the AI's language: Japanese stays, anything else is English."""
    return "ja" if lang == "ja" else "en"


class Words:
    """`w("send.title")` -> the text in this screen language; `w("send.placed", n=3, field="uncut")` fills it in."""

    def __init__(self, lang: str = "ja"):
        self.lang = screen_language(lang)
        self._i = SCREEN.index(self.lang)

    def __call__(self, key: str, **values) -> str:
        text = TEXTS[key][self._i]
        return text.format(**values) if values else text

    def has(self, key: str) -> bool:
        return key in TEXTS


def words(lang: str | None = None) -> Words:
    """The words for `lang`, or for the language now in use (llm.language: the setting, the device's, this machine's)."""
    return Words(lang or llm.language())
