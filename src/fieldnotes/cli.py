"""The `fieldnotes` command: run the pipeline and read or mark records from a terminal.

    fieldnotes init --place P --country CC --lat LAT --lon LON   start a farm (records/site.md)
    fieldnotes observe <field> [YYYY-MM-DD]          run the pipeline (default today)
    fieldnotes show <field> [YYYY-MM-DD]             print the record (default the latest)
    fieldnotes voice <field> <recording> [YYYY-MM-DD]  what you did and saw, or right/wrong, said aloud
    fieldnotes mark <field> <date> <key> right|wrong [reason] [--proposal cut|cover_crop]
    fieldnotes concept <field> <noun> right|wrong [reason] [--replace NOUN]
    fieldnotes propose <field> [--cut]               cover-crop proposal (or where to cut first) from the latest record
    fieldnotes compare [YYYY-MM-DD]                  rank fields (latest record of each)
    fieldnotes timeline <field> [--since DATE]       one field day by day
    fieldnotes surroundings                          fetch maps + read once
    fieldnotes lookup                                geology, soil, history from open data
    fieldnotes search <words> [--save]               look for a name near the farm
    fieldnotes consent [yes|no]                      may Meta train on what Spark is sent
    fieldnotes reader [spark|glimmer] [--url URL] [--model NAME] [--check]
                                                     which model reads the fields
    fieldnotes language [auto|ja|en|...]             the language the AI writes in
    fieldnotes app [--port 8550]                     the phone app
    fieldnotes mcp [--http [--port 8551]]            the tools for the farmer's own AI (MCP)

`--root DIR` (before the subcommand) is the folder that holds photos/ and
records/; it defaults to $FIELDNOTES_ROOT, else the current folder.
Messages for the farmer are in the screen language (ui.py).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

from . import concepts, lookup, pipeline, propose, site, surroundings, timeline, voice
from . import llm
from .llm import Backend
from .records import Record
from .ui import words


def _day(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(words()("cli.bad_date", text=repr(text))) from None


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

    s = sub.add_parser("voice", help="file a recording: what you did and saw, or which lines are right or wrong")
    s.add_argument("field")
    s.add_argument("recording", type=Path, help="m4a, 3gp, ogg, webm or WAV from the phone")
    s.add_argument("date", nargs="?", type=_day, default=None)

    s = sub.add_parser("mark", help="mark one AI line right or wrong")
    s.add_argument("field")
    s.add_argument("date", type=_day)
    s.add_argument("key", help="line key, e.g. dominant; key#2 for the second line with that key")
    s.add_argument("verdict", choices=pipeline.VERDICTS)
    s.add_argument("reason", nargs="*")
    s.add_argument("--proposal", choices=[propose.KIND, propose.KIND_CUT],
                   help="mark a line of that day's proposal instead of the record")

    s = sub.add_parser("concept", help="mark a SAM noun right or wrong")
    s.add_argument("field")
    s.add_argument("noun")
    s.add_argument("verdict", choices=pipeline.VERDICTS)
    s.add_argument("reason", nargs="*")
    s.add_argument("--replace", metavar="NOUN", help="a noun to try in its place")

    s = sub.add_parser("propose", help="cover-crop proposal from the latest record")
    s.add_argument("field")
    s.add_argument("--seeds", default="", help="seeds on hand, comma separated (cover crop)")
    s.add_argument("--cut", action="store_true", help="where to cut first and how high, instead of a cover crop")

    s = sub.add_parser("compare", help="rank fields on the barometers")
    s.add_argument("date", nargs="?", type=_day, default=None)

    s = sub.add_parser("surroundings", help="fetch the maps around the farm and read them (once)")
    s.add_argument("--force", action="store_true", help="read again, replacing the farmer's marks")

    s = sub.add_parser("lookup", help="look up geology, soil and history for the farm (records/lookup.md)")

    s = sub.add_parser("search", help="look for a name near the farm (Wikipedia, OpenStreetMap)")
    s.add_argument("words", nargs="+")
    s.add_argument("--save", action="store_true", help="add what was found to records/lookup.md")

    s = sub.add_parser("app", help="serve the phone app")
    s.add_argument("--port", type=int, default=8550)

    s = sub.add_parser("timeline", help="one field day by day: photos, readings, work, marks, proposals")
    s.add_argument("field")
    s.add_argument("--since", type=_day, default=None)

    s = sub.add_parser("mcp", help="serve the tools to the farmer's own AI (Claude, ChatGPT, Muse Code ...) over MCP")
    s.add_argument("--http", action="store_true", help="Streamable HTTP on the LAN instead of stdio")
    s.add_argument("--port", type=int, default=8551)
    s.add_argument("--buyer", action="store_true", help="read-only tools for a buyer's AI (planned)")

    s = sub.add_parser("consent", help="show or set whether Meta may train on what Muse Spark is sent")
    s.add_argument("answer", nargs="?", choices=["yes", "no"])
    s = sub.add_parser("reader", help="show or choose the model that reads the fields (spark or glimmer)")
    s.add_argument("name", nargs="?", choices=list(llm.READERS))
    s.add_argument("--url", help=f"Glimmer server (default {llm.GLIMMER_URL})")
    s.add_argument("--model", help=f"Glimmer model name on that server (default {llm.GLIMMER_MODEL})")
    s.add_argument("--check", action="store_true", help="ask the server whether it answers")

    s = sub.add_parser("language", help="show or set the language the AI writes in (auto: each phone's or PC's own)")
    s.add_argument("code", nargs="?", help="auto, or a language code such as ja or en")
    return p


def _say(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _latest_or_fail(field: str, root: Path, day: date | None = None) -> Record:
    rec = pipeline.latest_record(field, root, day)
    if rec is None:
        raise FileNotFoundError(words()("cli.no_record", field=field))
    return rec


def run(args: argparse.Namespace) -> int:
    root, records = args.root.resolve(), args.root.resolve() / "records"
    w = words()
    today = date.today()

    if args.cmd == "init":
        path = records / site.FILE
        if path.exists():
            raise ValueError(w("cli.exists", path=path))
        if len(args.country) != 2 or not -90 <= args.lat <= 90 or not -180 <= args.lon <= 180:
            raise ValueError(w("cli.bad_place"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(site.template(args.place, args.country, args.lat, args.lon, args.climate, args.method),
                        encoding="utf-8")
        _say(w("cli.created", path=path))
    elif args.cmd == "observe":
        day = args.date or today
        rec = pipeline.run_observation(args.field, day, root, progress=_say)
        _say(w("cli.saved", path=Record.path_for(records, rec.field, rec.date)))
        print(rec.to_markdown())
    elif args.cmd == "show":
        rec = Record.load(records, args.field, args.date.isoformat()) if args.date else _latest_or_fail(args.field, root)
        print(rec.to_markdown())
    elif args.cmd == "voice":
        with tempfile.TemporaryDirectory() as tmp:  # file_voice moves its input; keep the farmer's file
            copy = Path(tmp) / args.recording.name
            shutil.copyfile(args.recording, copy)
            text, changed = voice.file_voice(copy, args.field, args.date or today, root)
        _say(w("cli.heard", text=text))
        for o in changed:
            print(o.to_line())
    elif args.cmd == "mark" and args.proposal:
        line = propose.mark(records, args.field, args.date.isoformat(), args.proposal, args.key, args.verdict,
                            _reason(args.reason))
        print(line.to_line())
    elif args.cmd == "mark":
        line = pipeline.mark(args.field, args.date, args.key, args.verdict, _reason(args.reason), root=root)
        print(line.to_line())
    elif args.cmd == "concept":
        shared = concepts.SharedConcepts.load(root / concepts.SHARED)
        concepts.mark(records, args.field, args.noun, args.verdict, _reason(args.reason), args.replace, shared)
        print(f"{args.noun}: {args.verdict}" + (f" → {args.replace}" if args.replace else ""))
    elif args.cmd == "propose":
        latest = _latest_or_fail(args.field, root)
        if args.cut:
            prop = propose.propose_cut(latest, today.isoformat(), records, Backend.default())
        else:
            seeds = [x.strip() for x in args.seeds.split(",") if x.strip()]
            prop = propose.propose_cover_crop(latest, today.isoformat(), records, Backend.default(), seeds)
        _say(w("cli.saved", path=prop.path_for(records, prop.field, prop.date, prop.kind)))
        print(prop.to_markdown())
    elif args.cmd == "compare":
        print(pipeline.compare_latest(args.date or today, root).to_markdown())
    elif args.cmd == "surroundings":
        path = surroundings.Surroundings.path(records)
        if path.exists() and not args.force:
            _say(w("cli.already", path=path))
        else:
            surroundings.read_surroundings(records, Backend.default())
            _say(w("cli.saved", path=path))
        print(path.read_text(encoding="utf-8"))
    elif args.cmd == "lookup":
        _say(w("cli.looking_up"))
        print(lookup.lookup(records).read_text(encoding="utf-8"))
    elif args.cmd == "search":
        query = " ".join(args.words)
        found = lookup.search(records, query)
        print("\n".join(found) or w("cli.nothing"))
        if args.save and found:
            path = records / lookup.FILE
            with path.open("a", encoding="utf-8") as f:
                f.write(f"\n## Search: {query} ({today.isoformat()})\n\n" + "\n".join(found) + "\n")
            _say(w("cli.appended", path=path))
    elif args.cmd == "consent":
        if args.answer:
            llm.set_training_consent(args.answer == "yes")
        c = llm.training_consent()
        state = w({None: "cli.consent_none", True: "cli.consent_yes", False: "cli.consent_no"}[c])
        print(w("cli.consent", state=state, model=llm.SPARK_CONTRIBUTOR if c else llm.SPARK))
    elif args.cmd == "language":
        if args.code:
            llm.set_language(args.code)
        w = words()  # the new setting may change the language
        lang = llm.language_label(llm.language())
        print(w("cli.lang_auto" if llm.language_setting() == llm.AUTO else "cli.lang_fixed", lang=lang))
    elif args.cmd == "reader":
        if args.name or args.url or args.model:
            llm.set_reader(args.name or llm.reader(), args.url, args.model)
        if llm.reader() == "glimmer":
            print(w("cli.reader_glimmer", name=w("reader.glimmer"), url=llm.glimmer_url(), model=llm.glimmer_model()))
        else:
            model = llm.SPARK_CONTRIBUTOR if llm.training_consent() else llm.SPARK
            print(w("cli.reader", name=w("reader.spark"), model=model))
            print(w("cli.glimmer_setting", url=llm.glimmer_url(), model=llm.glimmer_model()))
        if args.check:
            try:
                print(w("reader.ok", names=", ".join(llm.reachable(llm.Backend.default()))))
            except Exception as e:  # noqa: BLE001 - any failure means "not reachable"
                print(w("reader.ng", e=type(e).__name__))
                return 1
    elif args.cmd == "timeline":
        print(timeline.timeline(args.field, records, args.since.isoformat() if args.since else None), end="")
    elif args.cmd == "mcp":
        from . import mcp_server  # the MCP SDK loads only when serving
        if args.buyer:
            raise RuntimeError("--buyer is planned and not built yet")
        mcp_server.run(root, http=args.http, port=args.port)
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
        _say(words()("cli.error", e=e.args[0] if isinstance(e, KeyError) and e.args else e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
