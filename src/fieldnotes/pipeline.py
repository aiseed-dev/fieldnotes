"""STUB — drop this file at merge; WP1 (docs/implementation.md) owns the real pipeline.py.

It exists on the WP3 branch only so the phone app's 読む view can import and be
exercised. The signatures are exactly the ones in the contract.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from .records import Record

ROOT = Path(os.environ.get("FIELDNOTES_ROOT", ".")).resolve()


def run_observation(field: str, day: date, root: Path = ROOT, backend=None) -> Record:
    raise NotImplementedError("pipeline.py is a WP3 stub; the real one comes from WP1")


def mark(field: str, day: date, key: str, verdict: str, reason: str | None = None) -> None:
    """Set the farmer's verdict on the first observation line with this key."""
    records = ROOT / "records"
    rec = Record.load(records, field, day.isoformat())
    for o in rec.observations:
        if o.key == key:
            o.verdict, o.reason = verdict, reason
            rec.save(records)
            return
    raise KeyError(f"no {key!r} line in {field} {day}")
