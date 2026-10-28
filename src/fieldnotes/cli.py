"""The `fieldnotes` command: run the pipeline and read or mark records from a terminal.

    fieldnotes init --place P --country CC --lat LAT --lon LON   start a farm (records/site.md)
    fieldnotes observe <field> [YYYY-MM-DD]          run the pipeline (default today)
    fieldnotes show <field> [YYYY-MM-DD]             print the record (default the latest)
    fieldnotes mark <field> <date> <key> right|wrong [reason]
    fieldnotes concept <field> <noun> right|wrong [reason] [--replace NOUN]
    fieldnotes propose <field>                       cover-crop proposal from the latest record
    fieldnotes compare [YYYY-MM-DD]                  rank fields (latest record of each)
    fieldnotes surroundings                          fetch maps + read once
    fieldnotes consent [yes|no]                      may Meta train on what Spark is sent
    fieldnotes reader [spark|glimmer] [--url URL] [--model NAME] [--check]
                                                     which model reads the fields
    fieldnotes app [--port 8550]                     the phone app

`--root DIR` (before the subcommand) is the folder that holds photos/ and
records/; it defaults to $FIELDNOTES_ROOT, else the current folder.
Messages for the farmer are in Japanese.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from . import concepts, pipeline, propose, site, surroundings
from . import llm
from .llm import Backend
from .records import Record


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"日付は YYYY-MM-DD で: {text!r}") from None


def _reason(words: list[str]) -> str | None:
    return " ".join(words) or None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fieldnotes", description=__doc__.split("\n\n")[0])
    p.add_argument("--root", type=Path, default=pipeline.ROOT, help="folder with photos/ and records/")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="start a new farm: write records/site.md")
    s.add_argument("--place", required=True, help='e.g. "Tokushima, Japan"')
    s.add_argument("--country", required=True, help="ISO 3166 two-letter code, e.g. JP, US, KE")
    s.add_argument("--lat", type=float, required=True)
    s.add_argument("--lon", type=float, required=True)
    s.add_argument("--climate", default="", help='e.g. "warm temperate, humid"')
    s.add_argument("--method", default=site.METHOD, help="how the farm is worked")

    s = sub.add_parser("observe", help="run the pipeline on a day's photos")
    s.add_argument("field")
    s.add_argument("date", nargs="?", type=_day, default=None)

    s = sub.add_parser("show", help="print a record")
    s.add_argument("field")
    s.add_argument("date", nargs="?", type=_day, default=None)

    s = sub.add_parser("mark", help="mark one AI line right or wrong")
    s.add_argument("field")
    s.add_argument("date", type=_day)
    s.add_argument("key", help="line key, e.g. dominant; key#2 for the second line with that key")
    s.add_argument("verdict", choices=pipeline.VERDICTS)
    s.add_argument("reason", nargs="*")

    s = sub.add_parser("concept", help="mark a SAM noun right or wrong")
    s.add_argument("field")
    s.add_argument("noun")
    s.add_argument("verdict", choices=pipeline.VERDICTS)
    s.add_argument("reason", nargs="*")
    s.add_argument("--replace", metavar="NOUN", help="a noun to try in its place")

    s = sub.add_parser("propose", help="cover-crop proposal from the latest record")
    s.add_argument("field")
    s.add_argument("--seeds", default="", help="seeds on hand, comma separated")

    s = sub.add_parser("compare", help="rank fields on the barometers")
    s.add_argument("date", nargs="?", type=_day, default=None)

    s = sub.add_parser("surroundings", help="fetch the maps around the farm and read them (once)")
    s.add_argument("--force", action="store_true", help="read again, replacing the farmer's marks")

    s = sub.add_parser("app", help="serve the phone app")
    s.add_argument("--port", type=int, default=8550)

    s = sub.add_parser("consent", help="show or set whether Meta may train on what Muse Spark is sent")
    s.add_argument("answer", nargs="?", choices=["yes", "no"])
    s = sub.add_parser("reader", help="show or choose the model that reads the fields (spark or glimmer)")
    s.add_argument("name", nargs="?", choices=list(llm.READERS))
    s.add_argument("--url", help=f"Glimmer server (default {llm.GLIMMER_URL})")
    s.add_argument("--model", help=f"Glimmer model name on that server (default {llm.GLIMMER_MODEL})")
    s.add_argument("--check", action="store_true", help="ask the server whether it answers")
    return p


def _say(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _latest_or_fail(field: str, root: Path, day: date | None = None) -> Record:
    rec = pipeline.latest_record(field, root, day)
    if rec is None:
        raise FileNotFoundError(f"{field} の記録がありません。先に fieldnotes observe {field}")
    return rec


def run(args: argparse.Namespace) -> int:
    root, records = args.root.resolve(), args.root.resolve() / "records"
    today = date.today()

    if args.cmd == "init":
        path = records / site.FILE
        if path.exists():
            raise ValueError(f"{path} はもうあります。書き換えるなら手で編集してください")
        if len(args.country) != 2 or not -90 <= args.lat <= 90 or not -180 <= args.lon <= 180:
            raise ValueError("--country は2文字、--lat は -90〜90、--lon は -180〜180 です")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(site.template(args.place, args.country, args.lat, args.lon, args.climate, args.method),
                        encoding="utf-8")
        _say(f"作りました: {path}。畑ごとの写真は photos/<畑>/<日付>/ に入れて、fieldnotes observe <畑>")
    elif args.cmd == "observe":
        day = args.date or today
        rec = pipeline.run_observation(args.field, day, root, progress=_say)
        _say(f"保存しました: {Record.path_for(records, rec.field, rec.date)}")
        print(rec.to_markdown())
    elif args.cmd == "show":
        rec = Record.load(records, args.field, args.date.isoformat()) if args.date else _latest_or_fail(args.field, root)
        print(rec.to_markdown())
    elif args.cmd == "mark":
        line = pipeline.mark(args.field, args.date, args.key, args.verdict, _reason(args.reason), root=root)
        print(line.to_line())
    elif args.cmd == "concept":
        shared = concepts.SharedConcepts.load(root / concepts.SHARED)
        concepts.mark(records, args.field, args.noun, args.verdict, _reason(args.reason), args.replace, shared)
        print(f"{args.noun}: {args.verdict}" + (f" → {args.replace}" if args.replace else ""))
    elif args.cmd == "propose":
        latest = _latest_or_fail(args.field, root)
        seeds = [x.strip() for x in args.seeds.split(",") if x.strip()]
        prop = propose.propose_cover_crop(latest, today.isoformat(), records, Backend.default(), seeds)
        _say(f"保存しました: {prop.path_for(records, prop.field, prop.date, prop.kind)}")
        print(prop.to_markdown())
    elif args.cmd == "compare":
        print(pipeline.compare_latest(args.date or today, root).to_markdown())
    elif args.cmd == "surroundings":
        path = surroundings.Surroundings.path(records)
        if path.exists() and not args.force:
            _say(f"すでに読んであります: {path}（やり直すなら --force。印は消えます）")
        else:
            surroundings.read_surroundings(records, Backend.default())
            _say(f"保存しました: {path}")
        print(path.read_text(encoding="utf-8"))
    elif args.cmd == "consent":
        if args.answer:
            llm.set_training_consent(args.answer == "yes")
        c = llm.training_consent()
        state = {None: "まだ決めていません（標準のモデルを使います）",
                 True: "同意しています（安いモデル。送ったものが学習に使われることがあります）",
                 False: "同意していません（標準のモデル。学習に使われません）"}[c]
        print(f"AI の学習への利用: {state}\nモデル: {llm.SPARK_CONTRIBUTOR if c else llm.SPARK}")
    elif args.cmd == "reader":
        if args.name or args.url or args.model:
            llm.set_reader(args.name or llm.reader(), args.url, args.model)
        if llm.reader() == "glimmer":
            print(f"読む AI: {llm.READERS['glimmer']}\n接続先: {llm.glimmer_url()}\nモデル: {llm.glimmer_model()}")
        else:
            model = llm.SPARK_CONTRIBUTOR if llm.training_consent() else llm.SPARK
            print(f"読む AI: {llm.READERS['spark']}\nモデル: {model}")
            print(f"（Glimmer の設定: {llm.glimmer_url()}、{llm.glimmer_model()}）")
        if args.check:
            try:
                print("つながりました: " + ", ".join(llm.reachable(llm.Backend.default())))
            except Exception as e:  # noqa: BLE001 - any failure means "not reachable"
                print(f"つながりません: {type(e).__name__}")
                return 1
    elif args.cmd == "app":
        os.environ["FIELDNOTES_ROOT"] = str(root)  # app.py reads it when imported
        from . import app
        app.run(port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as e:
        _say(f"エラー: {e.args[0] if isinstance(e, KeyError) and e.args else e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
