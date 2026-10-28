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
    "tip.language": ("言語", "Language"),
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
    "around": ("近所（畑のまわり）", "Neighbourhood (around the fields)"),
    # 読む
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
    "step.read": ("{model} が畑を読んでいます", "{model} is reading the field"),
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
