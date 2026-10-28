"""The `fieldnotes` command: run the pipeline and read or mark records from a terminal.

    fieldnotes observe <field> [YYYY-MM-DD]          run the pipeline (default today)
    fieldnotes show <field> [YYYY-MM-DD]             print the record (default the latest)
    fieldnotes mark <field> <date> <key> right|wrong [reason]
    fieldnotes concept <field> <noun> right|wrong [reason] [--replace NOUN]
    fieldnotes propose <field>                       cover-crop proposal from the latest record
    fieldnotes compare [YYYY-MM-DD]                  rank fields (latest record of each)
    fieldnotes surroundings                          fetch maps + read once
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

from . import concepts, pipeline, propose, surroundings
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

    s = sub.add_parser("surroundings", help="fetch the GSI maps and read them (once)")
    s.add_argument("--force", action="store_true", help="read again, replacing the farmer's marks")

    s = sub.add_parser("app", help="serve the phone app")
    s.add_argument("--port", type=int, default=8550)
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

    if args.cmd == "observe":
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
        prop = propose.propose_cover_crop(latest, today.isoformat(), records, Backend.spark(), seeds)
        _say(f"保存しました: {prop.path_for(records, prop.field, prop.date, prop.kind)}")
        print(prop.to_markdown())
    elif args.cmd == "compare":
        print(pipeline.compare_latest(args.date or today, root).to_markdown())
    elif args.cmd == "surroundings":
        path = surroundings.Surroundings.path(records)
        if path.exists() and not args.force:
            _say(f"すでに読んであります: {path}（やり直すなら --force。印は消えます）")
        else:
            surroundings.read_surroundings(records, Backend.spark())
            _say(f"保存しました: {path}")
        print(path.read_text(encoding="utf-8"))
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
