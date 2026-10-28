"""The MCP tools, called the way the farmer's own AI calls them (the SDK's in-memory client)."""

from __future__ import annotations

import asyncio

from conftest import DAY, FIELD, add_photos
from mcp.client.client import Client

from fieldnotes import mcp_server, timeline
from fieldnotes.records import Record

D = DAY.isoformat()
TOOLS = {"fields", "read", "observe", "say", "mark", "propose", "timeline", "site"}


def call(server, *calls):
    """Run tool calls in order; returns each result's text (or "ERROR: ..." for a tool error)."""
    async def go():
        out = []
        async with Client(server) as c:
            out.append({t.name for t in (await c.list_tools()).tools})
            for name, args in calls:
                r = await c.call_tool(name, args)
                text = "\n".join(p.text for p in r.content if p.type == "text")
                out.append(("ERROR: " if r.is_error else "") + text)
        return out
    return asyncio.run(go())


def test_the_farmers_tools(root, model, sam, wx):
    add_photos(root)
    server = mcp_server.build(root)
    names, before, observed, read, said, marked, proposed, tl, fields, site = call(
        server,
        ("read", {"field": FIELD}),
        ("observe", {"field": FIELD, "day": D}),
        ("read", {"field": FIELD, "day": D}),
        ("say", {"field": FIELD, "day": D, "text": "東側を刈った。ダイコンに本葉。酸度は違う、スギナが少ない。"}),
        ("mark", {"field": FIELD, "day": D, "key": "overall", "verdict": "right"}),
        ("propose", {"field": FIELD, "kind": "cut"}),
        ("timeline", {"field": FIELD}),
        ("fields", {}),
        ("site", {}),
    )
    assert names == TOOLS
    assert before.startswith("ERROR:") and "call observe first" in before
    assert "## AI observation" in observed and observed == read
    assert "- work: 東側を刈って草マルチにした" in said and "→ farmer: wrong (スギナが少ないので酸性ではない)" in said
    assert marked.startswith("- overall: Even green cover") and marked.endswith("→ farmer: right")
    assert "## Cut proposal" in proposed and "- where: the south edge" in proposed
    assert f"## {D}" in tl and "work: 東側を刈って草マルチにした" in tl
    assert "farmer: 1 ✓, 1 ✗ of 4 AI lines" in tl and "cut proposal: summary: Cut the south edge first" in tl
    assert f"## {FIELD}" in fields and f"read on: {D}" in fields
    assert "no records/site.md yet" in site
    rec = Record.load(root / "records", FIELD, D)
    assert "(the farmer's own AI)" not in rec.farmer_note and rec.note_model == "the farmer's own AI"


def test_mark_a_proposal_line(root, model, sam, wx):
    add_photos(root)
    server = mcp_server.build(root)
    from datetime import date
    today = date.today().isoformat()
    _, _, _, marked, bad = call(
        server,
        ("observe", {"field": FIELD, "day": D}),
        ("propose", {"field": FIELD, "kind": "cut"}),
        ("mark", {"field": FIELD, "day": today, "key": "height", "verdict": "wrong",
                  "reason": "too high", "proposal": "cut"}),
        ("propose", {"field": FIELD, "kind": "hedge"}),
    )
    assert marked.endswith("→ farmer: wrong (too high)")
    assert bad.startswith("ERROR:") and "cut or cover_crop" in bad


def test_timeline_without_records(root):
    assert timeline.timeline(FIELD, root / "records") == f"# {FIELD}: timeline\n\n(no records yet)\n"
