"""fieldnotes as MCP tools: the farmer works from the AI they already use.

There is no chat screen in fieldnotes. The farmer talks to their own AI
(Claude, ChatGPT, Muse Code ...), which calls these tools; the specialist
models (SAM 3.1, Muse Spark or Glimmer, Muse Voice Transcribe) do the reading
behind them. Photos and voice recordings still come in through the phone app.

    fieldnotes --root ~/myfarm mcp                  # stdio, for Claude Code / Claude Desktop
    fieldnotes --root ~/myfarm mcp --http           # Streamable HTTP on the LAN, port 8551

Each tool is a thin call of the function the CLI and the app use, and returns
Markdown, as the records already are.
"""

from __future__ import annotations

import functools
from datetime import date
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import check, pipeline, propose, timeline as timeline_mod, voice
from .appdata import photo_days
from .inbox import list_fields
from .llm import Backend
from .records import Record
from .site import Site

INSTRUCTIONS = """fieldnotes keeps the records of a natural-farming farm: per field and day, the photos, what Meta's models read in them (SAM 3.1 cover, Muse Spark's lines), what the farmer did and saw, and the farmer's right/wrong on every AI line.
In the records, a line ending in "→ farmer: right" or "→ farmer: wrong (reason)" was checked by the farmer; a line without it is only the AI's reading. Keep the two apart when you tell the farmer or anyone else what the records say.
Mark a line right or wrong only when the farmer says so; never on your own judgement. Pass what the farmer tells you about the field to `say`, in their words."""


def _day(day: str | None, default: date | None = None) -> date | None:
    return date.fromisoformat(day) if day else default


def _said(fn):
    """Errors the farmer can act on (no record yet, a bad date or key) reach their AI as the message,
    not as a bare "error executing tool"."""
    @functools.wraps(fn)
    def call(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (FileNotFoundError, ValueError, KeyError, RuntimeError) as e:
            raise ToolError(e.args[0] if isinstance(e, KeyError) and e.args else str(e)) from e
    return call


def build(root: Path, buyer: bool = False) -> MCPServer:
    """The server for the farm folder `root`. `buyer` (9b, not built yet) will
    register only the read-only tools."""
    if buyer:
        raise NotImplementedError("--buyer is planned (WP9b) and not built yet")
    root = root.resolve()
    records = root / "records"
    server = MCPServer("fieldnotes", instructions=INSTRUCTIONS)

    @server.tool()
    @_said
    def fields() -> str:
        """The farm's place and its fields: for each field, the days with photos and the days already read."""
        site = Site.load(records)
        out = [f"# Farm: {site.place or '(no records/site.md yet)'}" + (f" ({site.country})" if site.country else ""),
               f"method: {site.method}", ""]
        for f in list_fields(root / "photos", records):
            out.append(f"## {f}")
            out.append("photos on: " + (", ".join(photo_days(root / "photos", f)) or "-"))
            out.append("read on: " + (", ".join(pipeline.record_dates(f, root)) or "-"))
            out.append("")
        return "\n".join(out)

    @server.tool()
    @_said
    def read(field: str, day: str | None = None) -> str:
        """The record of one field on one day (YYYY-MM-DD), or the newest record when no day is given."""
        rec = Record.load(records, field, day) if day else pipeline.latest_record(field, root)
        if rec is None:
            raise FileNotFoundError(f"no record for {field} yet; call observe first")
        return rec.to_markdown()

    @server.tool()
    @_said
    def observe(field: str, day: str | None = None) -> str:
        """Read a field's photos of one day (default today) with SAM 3.1 and the chosen reading model,
        and save the record. Takes one to several minutes. Returns the record."""
        return pipeline.run_observation(field, _day(day, date.today()), root).to_markdown()

    @server.tool()
    @_said
    def say(field: str, text: str, day: str | None = None) -> str:
        """What the farmer said about a field (default today), in their own words: what they did, what they saw,
        or which AI lines are right or wrong and why. Kept word for word and sorted into the record.
        Returns the lines it added or marked."""
        changed = voice.file_text(text, field, _day(day, date.today()), root, heard_by="the farmer's own AI")
        return "\n".join(o.to_line() for o in changed) or "(kept as the farmer's note; nothing to sort)"

    @server.tool()
    @_said
    def mark(field: str, day: str, key: str, verdict: str, reason: str | None = None,
             proposal: str | None = None) -> str:
        """Set the farmer's verdict ("right" or "wrong", with the reason) on one line: a record line by its key
        (overall, dominant, acidity ..., work, seen, h3 for the check of hypothesis 3; key#2 for the second line
        with that key), a line of that day's proposal when `proposal` is "cut" or "cover_crop", or one of the
        field's expectations (h3) when `proposal` is "expect". Only when the farmer says so."""
        if proposal == "expect":
            line = check.mark(records, field, key, verdict, reason)
        elif proposal:
            line = propose.mark(records, field, day, proposal, key, verdict, reason)
        else:
            line = pipeline.mark(field, _day(day), key, verdict, reason, root=root)
        return line.to_line()

    @server.tool(name="propose")
    @_said
    def propose_(field: str, kind: str = "cut", seeds: str | None = None) -> str:
        """Propose for a field from its newest record: kind "cut" (where to cut first and how high, on a plot
        gone wild) or "cover_crop" (a green-manure mix; `seeds` = seeds on hand, comma separated). Saved as a
        proposal the farmer marks line by line. Takes about a minute."""
        latest = pipeline.latest_record(field, root)
        if latest is None:
            raise FileNotFoundError(f"no record for {field} yet; call observe first")
        today = date.today().isoformat()
        if kind == propose.KIND_CUT:
            prop = propose.propose_cut(latest, today, records, Backend.default())
        elif kind == propose.KIND:
            on_hand = [x.strip() for x in (seeds or "").split(",") if x.strip()]
            prop = propose.propose_cover_crop(latest, today, records, Backend.default(), on_hand)
        else:
            raise ValueError(f"kind is cut or cover_crop, not {kind!r}")
        return prop.to_markdown()

    @server.tool()
    @_said
    def timeline(field: str, since: str | None = None) -> str:
        """One field day by day, oldest first: photos, weather, the overall reading, what the farmer did and saw,
        how many AI lines the farmer marked right and wrong, and the proposals."""
        return timeline_mod.timeline(field, records, since)

    @server.tool()
    @_said
    def site() -> str:
        """What is known about the farm's place: records/site.md (each line marked data, record or hypothesis)
        and the open data looked up for it (records/lookup.md)."""
        parts = [p.read_text(encoding="utf-8") for p in (records / "site.md", records / "lookup.md") if p.exists()]
        return "\n\n".join(parts) or "(no records/site.md yet; run fieldnotes init)"

    return server


def run(root: Path, http: bool = False, port: int = 8551) -> None:
    server = build(root)
    if http:
        server.run("streamable-http", host="0.0.0.0", port=port)
    else:
        server.run("stdio")
