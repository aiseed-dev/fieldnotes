"""Phone app: send field photos and voice recordings from an iPhone or Android browser.

Run on the house machine:

    .venv/bin/python -m fieldnotes.app            # http://<host>:8550

and open it on the phone (at home over Wi-Fi, in the field through
Tailscale). Pick the field, take or choose photos, send. Each photo lands in
photos/<field>/<date>/ (see inbox.py); no folder work by hand.

The views, switched from the bar at the bottom (docs/design.md §1.13):
送る / Send (this file's send_view), 読む / Read (run the pipeline, see the SAM
overlays and the AI's lines, mark each right or wrong), 土地 / Land (site.md
and lookup.md line by line with their sources, the hypotheses checked day by
day) and 名詞 / Nouns (the SAM noun phrases of a field, marked right or wrong
with a replacement).
Send and Read also take a voice recording (voice_button, voice.py): what the
farmer did and saw, or which lines are right or wrong and why.

The screen is in Japanese or English, following the language the AI writes
in (ui.py); every view takes the page's `w` for its words.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import time
from datetime import date
from pathlib import Path

import flet as ft
import flet.canvas as cv

from . import appdata, concepts, llm, pipeline, voice
from .inbox import AROUND, file_photo, list_fields, valid_field
from .records import Observation, Record
from .ui import Words

ROOT = Path(os.environ.get("FIELDNOTES_ROOT", ".")).resolve()
PHOTOS = ROOT / "photos"
RECORDS = ROOT / "records"
UPLOADS = ROOT / "uploads"
NEW = "__new__"


def send_view(page: ft.Page, dialogs: "Dialogs", w: Words, lang: str | None = None) -> ft.Control:
    """送る: pick the field and day, choose photos, upload; each lands in photos/ via inbox.file_photo."""
    fields = list_fields(PHOTOS, RECORDS)
    field_dd = ft.Dropdown(
        label=w("field"),
        options=[ft.DropdownOption(key=f, text=f) for f in fields] + [
            ft.DropdownOption(key=AROUND, text=w("around")), ft.DropdownOption(key=NEW, text=w("send.new_field"))],
        value=fields[0] if fields else NEW,
        expand=True,
    )
    new_field = ft.TextField(label=w("send.new_field_name"), visible=not fields)
    day = ft.TextField(label=w("send.day"), value=date.today().isoformat(), read_only=True)  # no keyboard in the field: a calendar

    def pick_day(e=None):
        def picked(ev):
            if ev.control.value:
                day.value = ev.control.value.date().isoformat() if hasattr(ev.control.value, "date") else str(ev.control.value)[:10]
                show_walk()
                page.update()
        page.show_dialog(ft.DatePicker(value=chosen_day() or date.today(), first_date=date(2000, 1, 1),
                                       last_date=date(date.today().year + 1, 12, 31), on_change=picked))

    day.on_click = pick_day
    day.suffix = ft.IconButton(ft.Icons.CALENDAR_MONTH, on_click=pick_day, tooltip=w("send.day"))
    status = ft.Text("")
    progress = ft.ProgressBar(value=0, visible=False)
    sent = ft.Column(spacing=4)
    walk = ft.Column(spacing=6)

    def show_walk(e=None):
        """The day's photos so far, as the strip in walk order with the map."""
        walk.controls.clear()
        field, d = chosen_field(), chosen_day()
        if field and d:
            walk.controls.append(walk_strip(page, dialogs, w, field, d.isoformat(), open_photo=True))
        if e is not None:
            page.update()

    def on_field_change(e):
        new_field.visible = field_dd.value == NEW
        show_walk(e)

    field_dd.on_select = on_field_change
    new_field.on_change = day.on_change = show_walk

    batch: dict = {}

    def chosen_field() -> str | None:
        name = (new_field.value or "").strip() if field_dd.value == NEW else field_dd.value
        return name if name and (valid_field(name) or name == AROUND) else None

    def chosen_day() -> date | None:
        try:
            return date.fromisoformat((day.value or "").strip())
        except ValueError:
            return None

    def on_upload(e: ft.FilePickerUploadEvent):
        if e.error:
            status.value = w("send.failed", name=e.file_name, error=e.error)
            page.update()
            return
        if e.progress is None or e.progress < 1.0:
            return
        batch["done"] += 1
        batch["left"].discard(e.file_name)
        progress.value = batch["done"] / batch["total"]
        try:
            dest = file_photo(UPLOADS / batch["dir"] / e.file_name, batch["field"], batch["day"], PHOTOS)
            sent.controls.insert(0, ft.Text(f"✓ {dest.relative_to(ROOT)}", size=13))
        except Exception as ex:  # one bad file should not stop the rest
            sent.controls.insert(0, ft.Text(f"✗ {e.file_name}: {ex}", size=13, color=ft.Colors.ERROR))
        if batch["done"] == batch["total"]:
            status.value = w("send.placed", n=batch["total"], field=appdata.place_label(batch["field"], w))
            progress.visible = False
            show_walk(e)
        else:
            status.value = w("send.left", n=len(batch["left"]), names=", ".join(sorted(batch["left"])[:5]))
        page.update()

    picker = ft.FilePicker(on_upload=on_upload)
    page.services.append(picker)

    async def pick_and_send(e):
        field, d = chosen_field(), chosen_day()
        if not field:
            status.value = w("send.bad_field")
            page.update()
            return
        if not d:
            status.value = w("send.bad_day")
            page.update()
            return
        files = await picker.pick_files(file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True,
                                        cancel_upload_on_window_blur=False)
        if not files:
            return
        sub = secrets.token_hex(4)
        batch.update(dir=sub, field=field, day=d, total=len(files), done=0, left={f.name for f in files})
        progress.value, progress.visible = 0, True
        status.value = w("send.sending", n=len(files))
        page.update()
        await picker.upload(files=[
            ft.FilePickerUploadFile(id=f.id, name=f.name, upload_url=page.get_upload_url(f"{sub}/{f.name}", 600))
            for f in files
        ])

    def voice_target():
        field, d = chosen_field(), chosen_day()
        if not field or not d:
            status.value = w("send.bad_field") if not field else w("send.bad_day")
            page.update()
            return None
        return field, d

    show_walk()
    return ft.Column([
        ft.Text(w("send.title"), size=22, weight=ft.FontWeight.BOLD),
        ft.Row([field_dd]),
        new_field,
        day,
        ft.FilledButton(w("send.button"), icon=ft.Icons.PHOTO_CAMERA, on_click=pick_and_send,
                        style=ft.ButtonStyle(padding=20), expand=True),
        progress,
        status,
        sent,
        walk,
        voice_button(page, w, w("voice.button"), voice_target, lang),
    ])

def voice_button(page: ft.Page, w: Words, label: str, target, lang: str | None, on_done=None) -> ft.Control:
    """A button that takes a recording (the phone's recorder, or a file), keeps it
    next to the day's photos and sorts what was said into the record (voice.py).
    `target()` returns (field, day), or None after saying what is missing."""
    status = ft.Text("", size=14, selectable=True)
    busy = ft.Row([ft.ProgressRing(width=24, height=24), ft.Text("", expand=True)], visible=False, spacing=12)
    job: dict = {}

    async def work(path: Path):
        t0 = time.monotonic()
        busy.visible, status.value = True, ""
        llm.device_language.set(lang)  # the thread inherits it: the transcript and sorting are in the farmer's language
        task = asyncio.create_task(asyncio.to_thread(voice.file_voice, path, job["field"], job["day"], ROOT))
        while not task.done():
            busy.controls[1].value = w("voice.working", s=int(time.monotonic() - t0))
            page.update()
            await asyncio.sleep(1)
        busy.visible = False
        try:
            text, changed = task.result()
            status.value = w("voice.done", text=text) + "\n" + w("voice.sorted", n=len(changed))
            status.color = None
        except Exception as ex:
            status.value, status.color = w("voice.failed", e=ex), ft.Colors.ERROR
        if on_done:
            on_done()
        page.update()

    def on_upload(e: ft.FilePickerUploadEvent):
        if e.error:
            status.value, status.color = w("send.failed", name=e.file_name, error=e.error), ft.Colors.ERROR
            page.update()
        elif e.progress is not None and e.progress >= 1.0:
            page.run_task(work, UPLOADS / job["dir"] / e.file_name)

    picker = ft.FilePicker(on_upload=on_upload)
    page.services.append(picker)

    async def pick(e):
        sel = target()
        if not sel:
            return
        files = await picker.pick_files(file_type=ft.FilePickerFileType.AUDIO, allow_multiple=False,
                                        cancel_upload_on_window_blur=False)
        if not files:
            return
        f = files[0]
        job.update(dir=secrets.token_hex(4), field=sel[0], day=date.fromisoformat(str(sel[1])))
        status.value, status.color = w("voice.sending"), None
        page.update()
        await picker.upload(files=[ft.FilePickerUploadFile(
            id=f.id, name=f.name, upload_url=page.get_upload_url(f"{job['dir']}/{f.name}", 600))])

    return ft.Column([ft.FilledTonalButton(label, icon=ft.Icons.MIC, on_click=pick, height=56,
                                           style=ft.ButtonStyle(padding=20), expand=True),
                      busy, status], spacing=8)


THUMB = 164  # two thumbnails side by side in 375 px minus the 16 px page padding
GOOD, BAD = ft.Colors.GREEN_700, ft.Colors.RED_700


def verdict_row(w: Words, current: str | None, on_right, on_wrong, short: bool = False) -> ft.Row:
    """✓ / ✗ as two large buttons a thumb apart; the one matching `current` is filled.
    `short` keeps only the marks, for a half-width column."""
    def button(label: str, color, picked: bool, on_click):
        cls = ft.FilledButton if picked else ft.OutlinedButton
        kw = {"style": ft.ButtonStyle(bgcolor=color, color=ft.Colors.WHITE)} if picked else {"style": ft.ButtonStyle(color=color)}
        return cls(label, on_click=on_click, expand=True, height=48, **kw)

    right, wrong = ("✓", "✗") if short else (w("right"), w("wrong"))
    return ft.Row([button(right, GOOD, current == "right", on_right),
                   button(wrong, BAD, current == "wrong", on_wrong)], spacing=12 if short else 24)


class Dialogs:
    """The few pop-ups the views share: a form, a big photo, a short message."""

    def __init__(self, page: ft.Page, w: Words):
        self.page, self.w = page, w

    def say(self, text: str, error: bool = False):
        self.page.show_dialog(ft.SnackBar(ft.Text(text), bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
                                          duration=4000 if error else 2000))

    def form(self, title: str, fields: list[ft.TextField], on_save):
        def save(e):
            self.page.pop_dialog()
            on_save()

        width = min(self.page.width or 360, 480) - 96
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(title, size=18),
            content=ft.Column(fields, tight=True, width=width, spacing=12),
            actions=[ft.TextButton(self.w("cancel"), on_click=lambda e: self.page.pop_dialog(), height=48),
                     ft.FilledButton(self.w("save"), on_click=save, height=48)],
            inset_padding=16,
        ))

    def text(self, title: str, body: str):
        """A long text to read and select, whole."""
        w = min(self.page.width or 360, 900) - 32
        h = (self.page.height or 640) - 200
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(title, size=16),
            content=ft.Container(ft.Column([ft.Text(body, size=15, selectable=True)], scroll=ft.ScrollMode.AUTO), width=w, height=h),
            actions=[ft.TextButton(self.w("close"), on_click=lambda e: self.page.pop_dialog(), height=48)],
            content_padding=12, inset_padding=8,
        ))

    def photo(self, path: Path, title: str):
        w = min(self.page.width or 360, 900) - 32
        h = (self.page.height or 640) - 160
        image = ft.Image(src=appdata.shrunk_jpeg(path, 1600), fit=ft.BoxFit.CONTAIN)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(title, size=16),
            content=ft.Container(ft.InteractiveViewer(image, min_scale=1, max_scale=5), width=w, height=h),
            actions=[ft.TextButton(self.w("close"), on_click=lambda e: self.page.pop_dialog(), height=48)],
            content_padding=8, inset_padding=8,
        ))


def card(*controls: ft.Control, expand: bool = False) -> ft.Container:
    return ft.Container(ft.Column(list(controls), spacing=8), padding=12, border_radius=8,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT), expand=expand)


MAP_H = 170  # the walk map's height; its width is the screen's
STRIP_W, STRIP_H = 96, 72  # one thumbnail in the strip


def walk_strip(page: ft.Page, dialogs: Dialogs, w: Words, field: str, day: str, open_photo: bool = True) -> ft.Column:
    """The day's photos as a strip in walk order under a map of where each was taken: the
    GPS points numbered on the parcel outline (or the walk's extent) the way walk.py places
    them (appdata.walk_map). A tap on a thumbnail moves the marker to its point and, in Read,
    opens the photo or its SAM overlay. Says plainly when there is no GPS."""
    items = appdata.strip(ROOT, field, day)
    if not items:
        return ft.Column([ft.Text(w("walk.none"), size=14, color=ft.Colors.ON_SURFACE_VARIANT)])
    width = min(page.width or 360, 600) - 32
    m = appdata.walk_map([i.entry for i in items], RECORDS, width, MAP_H)
    overlays = sum(1 for i in items if i.overlay)
    note = w("walk.parcel") if m.kind == "parcel" else w("walk.extent") if m.kind == "walk" else w("walk.no_gps")
    head = ft.Text(w("walk.count", n=len(items), gps=m.n_gps, note=note)
                   + ("　" + w("read.with_sam") if overlays else ""), size=14)

    shapes: list = []
    outline = ft.Paint(color=ft.Colors.OUTLINE, stroke_width=2, style=ft.PaintingStyle.STROKE)
    for ring in m.rings:
        shapes.append(cv.Path([cv.Path.MoveTo(*ring[0])] + [cv.Path.LineTo(x, y) for x, y in ring[1:]] + [cv.Path.Close()],
                              paint=outline))
    route = [p for p in m.points if p]
    if len(route) > 1:  # the walk, as a dashed line through the points in order
        shapes.append(cv.Path([cv.Path.MoveTo(*route[0])] + [cv.Path.LineTo(x, y) for x, y in route[1:]],
                              paint=ft.Paint(color=ft.Colors.PRIMARY, stroke_width=1, style=ft.PaintingStyle.STROKE,
                                             stroke_dash_pattern=[4, 4])))
    dot = ft.Paint(color=ft.Colors.PRIMARY, style=ft.PaintingStyle.FILL)
    for i, p in zip(items, m.points):
        if p:
            shapes.append(cv.Circle(p[0], p[1], 5, paint=dot))
            shapes.append(cv.Text(p[0] + 6, p[1] - 6, str(i.n), style=ft.TextStyle(size=10, color=ft.Colors.ON_SURFACE)))
    marker = ft.Container(width=20, height=20, border_radius=10, border=ft.Border.all(3, ft.Colors.ERROR), visible=False,
                          animate_position=ft.Animation(300, ft.AnimationCurve.EASE_OUT))
    stack = ft.Stack([cv.Canvas(shapes, width=width, height=MAP_H), marker], width=width, height=MAP_H)
    chosen = ft.Text("", size=13, color=ft.Colors.ON_SURFACE_VARIANT)

    def select(i: int):
        """Move the marker to photo i's point (it slides there) and name the photo."""
        p = m.points[i]
        marker.visible = p is not None
        if p:
            marker.left, marker.top = p[0] - 10, p[1] - 10
        chosen.value = items[i].label
        page.update()

    def on_tap(e, i: int):
        select(i)
        if open_photo:
            it = items[i]
            dialogs.photo(it.overlay or it.photo, ("SAM " if it.overlay else "") + it.label)

    thumbs = ft.Row([ft.Container(
        ft.Stack([ft.Image(src=appdata.shrunk_jpeg(it.overlay or it.photo, 320), width=STRIP_W, height=STRIP_H,
                           fit=ft.BoxFit.COVER, border_radius=6),
                  ft.Container(ft.Text(str(it.n), size=11, color=ft.Colors.WHITE), bgcolor=ft.Colors.with_opacity(0.55, ft.Colors.BLACK),
                               padding=ft.Padding.symmetric(horizontal=5, vertical=1), border_radius=4, left=4, top=4)]),
        on_click=lambda e, i=i: on_tap(e, i), tooltip=it.label) for i, it in enumerate(items)],
        scroll=ft.ScrollMode.AUTO, spacing=6)
    return ft.Column([head, stack if m.kind != "none" else ft.Container(), chosen, thumbs], spacing=6)


def read_view(page: ft.Page, dialogs: Dialogs, w: Words, lang: str | None):
    """読む: run the pipeline on a field and day, then show the SAM overlays and the
    AI's lines, each with ✓ / ✗ saved through pipeline.mark. Returns (view, refresh)."""
    field_dd = ft.Dropdown(label=w("field"), expand=True)
    day_dd = ft.Dropdown(label=w("read.day"), expand=True)
    read_btn = ft.FilledButton(w("read.button"), icon=ft.Icons.VISIBILITY, height=56, expand=True)
    busy = ft.Row([ft.ProgressRing(width=24, height=24), ft.Text("", expand=True)], visible=False, spacing=12)
    status = ft.Text("")
    who = ft.Text("", size=14, color=ft.Colors.ON_SURFACE_VARIANT)
    photos = ft.Column(spacing=8)
    lines = ft.Column(spacing=10)
    running = {"on": False}

    def chosen() -> tuple[str, str] | None:
        return (field_dd.value, day_dd.value) if field_dd.value and day_dd.value else None

    def refresh(e=None):
        """Re-scan photos/ (the 送る view may have added some) and redraw."""
        who.value = appdata.reader_line(w, lang)
        fields = appdata.photo_fields(PHOTOS)
        field_dd.options = [ft.DropdownOption(key=f, text=appdata.place_label(f, w)) for f in fields]
        if field_dd.value not in fields:
            field_dd.value = fields[0] if fields else None
        fill_days()

    def fill_days(e=None):
        days = appdata.photo_days(PHOTOS, field_dd.value) if field_dd.value else []
        day_dd.options = [ft.DropdownOption(
            key=d, text=d + ("　" + w("read.done_mark") if Record.path_for(RECORDS, field_dd.value, d).exists() else ""))
            for d in days]
        if day_dd.value not in days:
            day_dd.value = days[0] if days else None
        read_btn.disabled = running["on"] or not days
        status.value = "" if days else w("read.no_photos")
        show()

    def show(e=None):
        """The walk strip (with overlays once read) and the record's lines for the chosen field and day."""
        photos.controls.clear()
        lines.controls.clear()
        sel = chosen()
        if sel:
            photos.controls.append(walk_strip(page, dialogs, w, *sel))
            show_lines()
        page.update()

    count = {"text": ft.Text("")}  # the day's mark count, redrawn with the lines and after each mark

    def show_lines():
        """The day's lines, each a row to mark, headed by the model and date that wrote them and
        what the model was given; a second reading of the same day (appdata.readings) stands
        beside the first for the same key. The count of marks at the top."""
        lines.controls.clear()
        field, day = chosen()
        found = appdata.readings(ROOT, field, day)
        state = [ft.Text(t, size=16, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True)
                 for t in appdata.day_state(ROOT, field, day, found[0].record if found else None, w)]
        if not found:
            lines.controls += state
            return
        rec = found[0].record
        count["text"] = ft.Text(appdata.count_label(rec, w), size=18, weight=ft.FontWeight.BOLD)
        lines.controls.append(count["text"])
        lines.controls += state
        two = len(found) > 1
        if two:  # which reading is which, once at the top
            lines.controls.append(ft.Row([ft.Text(
                w("read.earlier") if r.label == "earlier" else w("read.from", label=r.label),
                size=13, weight=ft.FontWeight.BOLD, expand=True) for r in found], spacing=8))
        heading = {"ai": w("read.question"), "voice": w("voice.heading"), "checks": w("read.checks")}
        shown = None
        rows = appdata.side_by_side(found)
        for group, ref, cells in rows:
            if group != shown:
                shown = group
                lines.controls.append(ft.Text(heading[group], size=18, weight=ft.FontWeight.BOLD))
                for r in found:  # the model, the date and the sources of each reading of this group
                    if r.label != "earlier" and any(x.group == group for x in r.refs):
                        lines.controls.append(ft.Text(
                            (f"{r.label}: " if two else "") + w("read.by", model=appdata.model_of(r.record, group), date=r.record.date)
                            + "　" + appdata.sources(r.record, (r.root or ROOT) / "records", w),
                            size=12, color=ft.Colors.ON_SURFACE_VARIANT))
            if not two:
                lines.controls.append(line_row(cells[0], found[0], field, day))
            else:
                lines.controls.append(ft.Row([
                    line_row(c, r, field, day, short=True) if c else ft.Container(
                        ft.Text(w("read.only_here"), size=13, color=ft.Colors.ON_SURFACE_VARIANT), padding=12, expand=True)
                    for c, r in zip(cells, found)], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START))
        if not rows:
            lines.controls.append(ft.Text(w("read.empty")))
        if rec.farmer_note:
            lines.controls.append(card(ft.Text(w("read.note"), size=13), ft.Text(rec.farmer_note, selectable=True)))

    def line_row(r: appdata.LineRef, reading: appdata.Reading, field: str, day: str, short: bool = False) -> ft.Container:
        """One line as one row: the model that wrote it, the text and its confidence, ✓ and ✗ a
        thumb apart, and the reason box, which opens under ✗. Each mark is saved at once
        (pipeline.mark, into the folder the reading is from) and the row and the day's count
        are redrawn from the file, not the rest of the list."""
        text, conf = appdata.split_conf(r.line.text)
        head = appdata.key_label(r.line.key, w) + ("　" + w("read.confidence", c=conf) if conf else "")
        model = ft.Text(appdata.model_of(reading.record, r.group) + ", " + reading.record.date, size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT)
        reason = ft.TextField(label=w("what_wrong"), value=r.line.reason or "", dense=True, multiline=True,
                              min_lines=1, max_lines=4, visible=r.line.verdict == "wrong",
                              text_size=15, animate_size=ft.Animation(200, ft.AnimationCurve.EASE_OUT))
        buttons = ft.Row(spacing=12 if short else 24)
        now = {"reason": r.line.reason or ""}
        body = [ft.Text(head, size=13, color=ft.Colors.ON_SURFACE_VARIANT), ft.Text(text, size=16, selectable=True), model]
        if reading.root is None:  # the lines a re-run replaced keep the marks they had; not marked again
            mark = {"right": w("right"), "wrong": w("wrong")}.get(r.line.verdict, "")
            if mark:
                body.append(ft.Text(mark + (f"　{r.line.reason}" if r.line.reason else ""), size=14,
                                    color=GOOD if r.line.verdict == "right" else BAD))
            return card(*body, expand=True)
        box = card(*body, buttons, reason, expand=True)

        def apply(line: Observation):
            buttons.controls = verdict_row(w, line.verdict, lambda e: save("right"), lambda e: save("wrong"), short).controls
            buttons.spacing = 12 if short else 24
            reason.visible = line.verdict == "wrong"
            reason.value = now["reason"] = line.reason or ""

        def save(verdict: str):
            why = reason.value.strip() if verdict == "wrong" else None
            try:
                line = pipeline.mark(field, date.fromisoformat(day), r.ref, verdict, why or None, root=reading.root)
                if reading.root == ROOT:
                    count["text"].value = appdata.count_label(Record.load(RECORDS, field, day), w)
            except Exception as ex:
                dialogs.say(w("not_saved", e=ex), error=True)
                return
            apply(line)
            if verdict == "wrong" and not why:
                reason.focus()
            page.update()

        reason.on_submit = reason.on_blur = lambda e: save("wrong") if reason.visible and (
            reason.value.strip() != now["reason"]) else None
        apply(r.line)
        return box

    async def on_read(e):
        sel = chosen()
        if not sel or running["on"]:
            return
        field, day = sel
        running["on"] = True
        for c in (field_dd, day_dd, read_btn):
            c.disabled = True
        busy.visible = True
        status.value = ""
        t0 = time.monotonic()
        llm.device_language.set(lang)  # the task and its thread inherit it
        task = asyncio.create_task(asyncio.to_thread(pipeline.run_observation, field, date.fromisoformat(day), ROOT))
        while not task.done():  # the worker thread does the reading; this loop only keeps the screen alive
            busy.controls[1].value = w("read.running", s=int(time.monotonic() - t0))
            page.update()
            await asyncio.sleep(1)
        running["on"] = False
        busy.visible = False
        for c in (field_dd, day_dd, read_btn):
            c.disabled = False
        try:
            task.result()
            message = w("read.finished", s=int(time.monotonic() - t0))
        except Exception as ex:
            message = w("read.failed", e=ex)
        fill_days()  # "read" label, overlays, lines
        status.value = message
        page.update()

    field_dd.on_select = fill_days
    day_dd.on_select = show
    read_btn.on_click = on_read
    view = ft.Column([
        ft.Text(w("read.title"), size=22, weight=ft.FontWeight.BOLD), who,
        ft.Row([field_dd]), ft.Row([day_dd]),
        ft.Row([read_btn]), busy, status, photos, lines,
        voice_button(page, w, w("voice.answer"), chosen, lang, on_done=show),
    ], spacing=12)
    return view, refresh


def nouns_view(page: ft.Page, dialogs: Dialogs, w: Words):
    """名詞: the SAM noun phrases of a field and what each found last time; ✓ / ✗ and a
    replacement, saved through concepts.mark. Returns (view, refresh)."""
    field_dd = ft.Dropdown(label=w("field"), expand=True)
    items = ft.Column(spacing=10)
    shared_path = ROOT / concepts.SHARED

    def refresh(e=None):
        fields = list(dict.fromkeys(appdata.concept_fields(RECORDS) + list_fields(PHOTOS, RECORDS)))
        field_dd.options = [ft.DropdownOption(key=f, text=f) for f in fields]
        if field_dd.value not in fields:
            field_dd.value = fields[0] if fields else None
        show()

    def show(e=None):
        items.controls.clear()
        if field_dd.value:
            fc = concepts.FieldConcepts.load(RECORDS, field_dd.value)
            items.controls += [concept_card(c) for c in fc.items]
        else:
            items.controls.append(ft.Text(w("nouns.none")))
        page.update()

    def concept_card(c: concepts.Concept) -> ft.Container:
        field = field_dd.value
        by = w("by." + c.by) if w.has("by." + c.by) else c.by
        body = [ft.Text(c.noun, size=20, weight=ft.FontWeight.BOLD),
                ft.Text(w("nouns.target", t=c.target or "—"), size=14),
                ft.Text(w("nouns.last", by=by, last=appdata.last_label(c.last, w)), size=13, color=ft.Colors.ON_SURFACE_VARIANT)]
        if not c.active:
            body.append(ft.Text(w("nouns.unused") + (f" ({c.reason})" if c.reason else ""), size=14, color=BAD))
            return card(*body)

        def save(verdict: str, reason: str | None = None, replacement: str | None = None):
            try:
                concepts.mark(RECORDS, field, c.noun, verdict, reason or None, replacement or None,
                              shared=concepts.SharedConcepts.load(shared_path))
            except Exception as ex:
                dialogs.say(w("not_saved", e=ex), error=True)
                return
            show()

        def ask(e):
            reason = ft.TextField(label=w("what_wrong"), multiline=True, min_lines=2, max_lines=4,
                                  autofocus=True)
            repl = ft.TextField(label=w("nouns.replacement"), hint_text=w("nouns.hint"))
            dialogs.form(w("wrong_title", what=c.noun), [reason, repl],
                         lambda: save("wrong", reason.value.strip(), repl.value.strip().lower()))

        return card(*body, verdict_row(w, c.verdict, lambda e: save("right"), ask))

    field_dd.on_select = show
    view = ft.Column([
        ft.Text(w("nouns.title"), size=22, weight=ft.FontWeight.BOLD),
        ft.Text(w("nouns.help"), size=14),
        ft.Row([field_dd]), items,
    ], spacing=12)
    return view, refresh


STATUS_COLOR = {"data": ft.Colors.LIGHT_BLUE_400, "record": ft.Colors.LIGHT_GREEN_400, "hypothesis": ft.Colors.AMBER_400,
                "supported": ft.Colors.TEAL_300, "refuted": ft.Colors.RED_300, "reference": ft.Colors.BLUE_GREY_300}


def source_text(text: str, size: int) -> ft.Text:
    """A source line, its addresses as links."""
    return ft.Text(spans=[ft.TextSpan(t, url=u, style=ft.TextStyle(color=ft.Colors.PRIMARY, decoration=ft.TextDecoration.UNDERLINE) if u else None)
                          for t, u in appdata.link_parts(text)],
                   size=size, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True)


def land_row(line: appdata.LandLine, found: dict, w: Words) -> ft.Control:
    """One line of site.md or lookup.md: its status, the claim, who says so, and for a
    hypothesis how it is checked and what the days' photos said. A line with no status
    ("not reached on ...") stands as the file words it."""
    if not line.status:
        return ft.Text(line.text, size=14, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True)
    color = STATUS_COLOR.get(line.status, ft.Colors.OUTLINE)
    label = "land.status." + line.status
    body: list[ft.Control] = [
        ft.Text(w(label) if w.has(label) else line.status, size=13, weight=ft.FontWeight.BOLD, color=color),
        ft.Text(line.text, size=16, selectable=True),
    ]
    body.append(source_text(line.source, 13) if line.source
                else ft.Text(w("land.no_source"), size=13, italic=True, color=ft.Colors.ON_SURFACE_VARIANT))
    if line.check:
        body.append(ft.Text(w("land.check", check=line.check), size=14, selectable=True))
    if line.status == "hypothesis":
        checks = appdata.checks_of(found, line)
        if not checks:
            body.append(ft.Text(w("land.no_check"), size=14, color=ft.Colors.ON_SURFACE_VARIANT))
        for c in checks:
            if c.by_day:
                days = ", ".join(f"{appdata.short_day(d)} {appdata.answer_label(o, w)}" for d, o in c.by_day)
                text = w("land.by_day", field=c.field, id=c.id, days=days)
            else:
                text = w("land.not_checked_yet" if c.visible else "land.not_in_photos", field=c.field, id=c.id)
            body.append(ft.Text(text, size=14, color=ft.Colors.ON_SURFACE_VARIANT))
    return ft.Container(ft.Column(body, spacing=4), padding=ft.Padding.only(left=10, top=4, bottom=4),
                        border=ft.Border.only(left=ft.BorderSide(3, color)))


def hypotheses_table(dialogs: Dialogs, w: Words, field: str) -> ft.Control:
    """timeline's hypotheses table on the screen: one row per hypothesis, one column per day;
    a tap on a row or a cell shows the whole line."""
    from . import timeline
    days, rows = timeline.checks_rows(RECORDS, field, timeline.days_of(RECORDS, field))
    if not days:
        return ft.Text(w("land.table_none", field=field), size=16, color=ft.Colors.ON_SURFACE_VARIANT)

    def cell(h: str, words: str, o) -> ft.DataCell:
        if o is None:
            return ft.DataCell(ft.Text("—", size=14, color=ft.Colors.ON_SURFACE_VARIANT))
        color = {"right": GOOD, "wrong": BAD}.get(o.verdict)
        return ft.DataCell(ft.Text(appdata.answer_label(o, w), size=14, color=color),
                           on_tap=lambda e: dialogs.text(h, (words + "\n\n" if words else "") + o.to_line()[2:]))

    def name(h: str, words: str) -> ft.DataCell:
        short = words if len(words) <= 40 else words[:39] + "…"
        return ft.DataCell(ft.Text(f"{h} {short}", size=14, width=300, no_wrap=False, max_lines=2),
                           on_tap=lambda e: dialogs.text(h, words or h))

    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(w("land.table_head"), size=14))] + [ft.DataColumn(ft.Text(appdata.short_day(d), size=14)) for d in days],
        rows=[ft.DataRow([name(h, words)] + [cell(h, words, cells.get(d)) for d in days]) for h, words, cells in rows],
        column_spacing=16, horizontal_margin=4, data_row_min_height=44, data_row_max_height=60, heading_row_height=36)
    return ft.Column([ft.Text(appdata.checks_by(RECORDS, field, days, w), size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                      ft.Row([table], scroll=ft.ScrollMode.AUTO)], spacing=4)


def land_tools(page: ft.Page, dialogs: Dialogs, w: Words, lang: str | None, after):
    """What the command line does, from the Land view: start a farm (init) when there is no
    site.md, add what the farmer knows (note), and per field the timeline as text, the
    expectations (expect) and the proposals (propose). The model's work runs only on a
    press, in a thread, and its result is shown headed by the model and the date.
    `after` redraws the Land view once site.md changed. Returns (control, refresh)."""
    from . import check, note, propose, site as site_mod, timeline
    from .llm import Backend
    box = ft.Column(spacing=10)
    busy = ft.Row([ft.ProgressRing(width=24, height=24), ft.Text("", expand=True)], visible=False, spacing=12)
    status = ft.Text("", selectable=True)
    field_dd = ft.Dropdown(label=w("field"), expand=True)
    seeds = ft.TextField(label=w("tools.seeds"))
    running = {"on": False}

    def say(text: str):
        status.value = text
        page.update()

    async def run(what: str, fn, show):
        """fn() in a thread with a seconds counter; show(result) after, or the error said."""
        if running["on"]:
            return
        running["on"], busy.visible = True, True
        t0 = time.monotonic()
        llm.device_language.set(lang)
        task = asyncio.create_task(asyncio.to_thread(fn))
        while not task.done():
            busy.controls[1].value = w("tools.running", what=what, s=int(time.monotonic() - t0))
            page.update()
            await asyncio.sleep(1)
        running["on"], busy.visible = False, False
        try:
            show(task.result())
        except Exception as ex:  # noqa: BLE001 - said on the screen, not raised
            say(w("tools.failed", e=f"{type(ex).__name__}: {ex}"))

    def init_form() -> ft.Control:
        f = {k: ft.TextField(label=w("tools." + k)) for k in ("place", "country", "lat", "lon", "climate", "method")}
        f["lat"].keyboard_type = f["lon"].keyboard_type = ft.KeyboardType.NUMBER

        def create(e):
            try:
                path = appdata.init_site(RECORDS, *(f[k].value or "" for k in ("place", "country", "lat", "lon", "climate", "method")))
            except Exception as ex:  # noqa: BLE001
                say(w("tools.failed", e=ex))
                return
            say(w("tools.saved", path=path))
            after()

        return card(ft.Text(w("tools.init"), size=16, weight=ft.FontWeight.BOLD), *f.values(),
                    ft.FilledButton(w("tools.create"), on_click=create, height=48))

    def note_form() -> ft.Control:
        text = ft.TextField(label=w("tools.note_text"), multiline=True, min_lines=2, max_lines=5)
        source = ft.TextField(label=w("tools.note_source"))
        section = ft.Dropdown(label=w("tools.section"), value="works", expand=True,
                              options=[ft.DropdownOption(key=k, text=v) for k, v in note.SECTIONS.items()])

        def save(e):
            try:
                path, line = appdata.add_note(RECORDS, text.value or "", section.value or "works", date.today(), source.value or "")
            except Exception as ex:  # noqa: BLE001
                say(w("tools.failed", e=ex))
                return
            text.value = source.value = ""
            say(w("tools.saved", path=path) + "\n" + line)
            after()

        return ft.ExpansionTile(title=ft.Text(w("tools.note"), size=16, weight=ft.FontWeight.BOLD), expanded=False,
                                tile_padding=0, controls=[ft.Column([text, source, ft.Row([section]),
                                                                     ft.FilledButton(w("tools.save_note"), on_click=save, height=48)],
                                                                    spacing=8)])

    def show_file(path: Path):
        """A file the model wrote, headed by its model and date (front matter `model`, `date`)."""
        text, front = appdata.file_front(path)
        say(w("tools.saved", path=path))
        dialogs.text(w("tools.reading", model=front.get("model", "?"), date=front.get("date", "?")), text)

    def on_timeline(e):
        if field_dd.value:
            dialogs.text(field_dd.value, timeline.timeline(field_dd.value, RECORDS))

    def on_expect(e):
        if field_dd.value:
            fld = field_dd.value
            page.run_task(run, w("tools.expect"), lambda: check.expect(fld, ROOT, Backend.default(), date.today().isoformat()), show_file)

    def on_propose(cut: bool):
        def go(e):
            fld = field_dd.value
            if not fld:
                return
            names = [x.strip() for x in (seeds.value or "").split(",") if x.strip()]

            def work():
                latest = appdata.latest_record(ROOT, fld)
                if latest is None:
                    raise FileNotFoundError(w("cli.no_record", field=fld) if w.has("cli.no_record") else f"no record of {fld} yet")
                today = date.today().isoformat()
                prop = (propose.propose_cut(latest, today, RECORDS, Backend.default()) if cut
                        else propose.propose_cover_crop(latest, today, RECORDS, Backend.default(), names))
                return prop.path_for(RECORDS, prop.field, prop.date, prop.kind)
            page.run_task(run, w("tools.propose_cut" if cut else "tools.propose_cover"), work, show_file)
        return go

    def refresh():
        box.controls.clear()
        if not (RECORDS / site_mod.FILE).exists():
            box.controls.append(init_form())
        else:
            box.controls.append(note_form())
        fields = appdata.record_fields(ROOT)
        field_dd.options = [ft.DropdownOption(key=f, text=f) for f in fields]
        if field_dd.value not in fields:
            field_dd.value = fields[0] if fields else None
        if not fields:
            box.controls.append(ft.Text(w("tools.no_fields"), size=16, color=ft.Colors.ON_SURFACE_VARIANT))
            return
        box.controls += [
            ft.Text(w("tools.field_work"), size=16, weight=ft.FontWeight.BOLD), ft.Row([field_dd]),
            ft.OutlinedButton(w("tools.timeline"), icon=ft.Icons.VIEW_TIMELINE, on_click=on_timeline, height=48),
            ft.OutlinedButton(w("tools.expect"), icon=ft.Icons.RULE, on_click=on_expect, height=48),
            ft.OutlinedButton(w("tools.propose_cut"), icon=ft.Icons.CONTENT_CUT, on_click=on_propose(True), height=48),
            seeds,
            ft.OutlinedButton(w("tools.propose_cover"), icon=ft.Icons.GRASS, on_click=on_propose(False), height=48),
        ]

    control = ft.Column([ft.Text(w("tools.title"), size=18, weight=ft.FontWeight.BOLD), box, busy, status],
                        spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    return control, refresh


def land_view(page: ft.Page, dialogs: Dialogs, w: Words, lang: str | None = None):
    """土地: site.md and lookup.md line by line, the hypotheses day by day, and the place the
    fertiliser and soil-carbon baseline will take (WP17). Returns (view, refresh)."""
    filter_row = ft.Row(wrap=True, spacing=6, run_spacing=6)
    body = ft.Column(spacing=12)
    field_dd = ft.Dropdown(label=w("field"), expand=True)
    table = ft.Column(spacing=8)
    state: dict = {"status": None, "site": None, "lookup": None, "found": {}}

    def show_lines():
        site, lookup = state["site"], state["lookup"]
        pages = [p for p in (site, lookup) if p]
        counts = appdata.status_counts(pages)

        def chip(key: str | None, label: str) -> ft.Chip:
            def pick(e):
                state["status"] = None if state["status"] == key else key
                show_lines()
                page.update()
            return ft.Chip(ft.Text(label, size=14), selected=state["status"] == key, on_select=pick, show_checkmark=False)

        filter_row.controls = [chip(None, w("land.all", n=sum(counts.values())))] + [
            chip(k, f"{k} {n}") for k, n in counts.items()]
        body.controls.clear()
        for head, p, empty in ((w("land.site"), site, "land.no_site"),
                               (w("land.lookup", fetched=(lookup.front.get("fetched", "—") if lookup else "—")), lookup, "land.no_lookup")):
            body.controls.append(ft.Text(head, size=18, weight=ft.FontWeight.BOLD))
            if not p:
                body.controls.append(ft.Text(w(empty), size=16, color=ft.Colors.ON_SURFACE_VARIANT))
                continue
            if p is site and p.front:
                body.controls.append(card(*[ft.Text(f"{w('land.front.' + k) if w.has('land.front.' + k) else k}: {v}", size=14, selectable=True)
                                            for k, v in p.front.items()]))
            for s in p.sections:
                lines = [x for x in s.lines if state["status"] in (None, x.status)]
                if state["status"] and not lines:
                    continue
                rows = [land_row(x, state["found"], w) for x in lines] or [
                    ft.Text(w("land.section_empty"), size=14, color=ft.Colors.ON_SURFACE_VARIANT)]
                body.controls.append(ft.ExpansionTile(
                    title=ft.Text(f"{s.heading} ({len(s.lines)})", size=16, weight=ft.FontWeight.BOLD),
                    controls=[ft.Column(rows, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)],
                    expanded=len(s.lines) <= 12, tile_padding=0, controls_padding=ft.Padding.only(bottom=8),
                    expanded_cross_axis_alignment=ft.CrossAxisAlignment.STRETCH))
            body.controls.append(ft.TextButton(w("land.whole_file", name=p.name), height=48,
                                               on_click=lambda e, p=p: dialogs.text(p.name, p.text)))

    def show_table(e=None):
        table.controls.clear()
        if field_dd.value:
            table.controls.append(hypotheses_table(dialogs, w, field_dd.value))
        else:
            table.controls.append(ft.Text(w("land.table_no_field"), size=16, color=ft.Colors.ON_SURFACE_VARIANT))
        if e is not None:
            page.update()

    def redraw():
        refresh()
        page.update()

    tools, refresh_tools = land_tools(page, dialogs, w, lang, redraw)

    def refresh(e=None):
        refresh_tools()
        state["site"], state["lookup"] = appdata.land_page(RECORDS, "site.md"), appdata.land_page(RECORDS, "lookup.md")
        state["found"] = appdata.hypothesis_checks(RECORDS)
        fields = appdata.check_fields(RECORDS)
        field_dd.options = [ft.DropdownOption(key=f, text=f) for f in fields]
        if field_dd.value not in fields:
            field_dd.value = fields[0] if fields else None
        field_dd.visible = len(fields) > 1
        show_lines()
        show_table()

    field_dd.on_select = show_table
    view = ft.Column([
        ft.Text(w("land.title"), size=22, weight=ft.FontWeight.BOLD),
        ft.Text(w("land.help"), size=14),
        filter_row, body,
        ft.Text(w("land.table"), size=18, weight=ft.FontWeight.BOLD),
        ft.Text(w("land.table_help"), size=14),
        ft.Row([field_dd]), table,
        ft.Text(w("land.baseline"), size=18, weight=ft.FontWeight.BOLD),
        card(ft.Text(w("land.baseline_not_yet"), size=16)),
        tools,
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    return view, refresh


def ask_consent(page: ft.Page, dialogs: Dialogs, first: bool = False):
    """The farmer decides, before anything is sent, whether Meta may train on it."""
    w = dialogs.w

    def choose(agreed: bool):
        llm.set_training_consent(agreed)
        page.pop_dialog()
        dialogs.say(w("consent.saved_yes") if agreed else w("consent.saved_no"))

    current = llm.training_consent()
    now = "" if current is None else "\n\n" + w("consent.now", state=w("consent.agreed" if current else "consent.refused"))
    page.show_dialog(ft.AlertDialog(
        modal=first,
        title=ft.Text(w("consent.title"), size=18),
        content=ft.Text(w("consent.text") + now, size=15),
        actions=[ft.TextButton(w("consent.refuse"), on_click=lambda e: choose(False), height=48),
                 ft.FilledButton(w("consent.agree"), on_click=lambda e: choose(True), height=48)],
        inset_padding=16,
    ))


async def device_language(page: ft.Page) -> str | None:
    """The phone's or PC's own language: the browser's (navigator.language) or the device's first locale."""
    try:
        info = await page.get_device_info()
    except Exception:  # noqa: BLE001 - unknown; llm.language falls back
        return None
    if info is None:
        return None
    first = info.locales[0] if info.locales else None
    return llm.language_code(getattr(info, "language", None)) or (llm.language_code(first.language_code) if first else None)


def ask_language(page: ft.Page, dialogs: Dialogs, here: str | None, on_saved):
    """Choose the language the AI writes in, and so the screen's; by default each phone's or PC's own."""
    w = dialogs.w
    width = min(page.width or 360, 480) - 96
    choice = ft.Dropdown(label=w("lang.label"), value=llm.language_setting(), width=width, options=[
        ft.DropdownOption(key=llm.AUTO, text=w("lang.auto", lang=llm.language_label(here) if here else w("lang.unknown"))),
        *[ft.DropdownOption(key=code, text=label) for code, (_, label) in llm.LANGUAGES.items()]])

    def save(e):
        llm.set_language(choice.value or llm.AUTO)
        page.pop_dialog()
        on_saved()

    page.show_dialog(ft.AlertDialog(
        title=ft.Text(w("lang.title"), size=18),
        content=ft.Column([ft.Text(w("lang.help"), size=14), choice], tight=True, width=width, spacing=12),
        actions=[ft.TextButton(w("cancel"), on_click=lambda e: page.pop_dialog(), height=48),
                 ft.FilledButton(w("save"), on_click=save, height=48)],
        inset_padding=16,
    ))


def ask_reader(page: ft.Page, dialogs: Dialogs):
    """Choose which model reads the fields: Muse Spark on api.meta.ai, or
    Muse Glimmer on the house machine (photos never leave the house)."""
    w = dialogs.w
    group = ft.RadioGroup(value=llm.reader(), content=ft.Column(
        [ft.Radio(value=k, label=w("reader." + k)) for k in llm.READERS], tight=True))
    url = ft.TextField(label=w("reader.url"), value=llm.glimmer_url(), keyboard_type=ft.KeyboardType.URL)
    model = ft.TextField(label=w("reader.model"), value=llm.glimmer_model())
    result = ft.Text("", size=14)

    async def check(e):
        result.value = w("reader.checking")
        page.update()
        try:
            names = await asyncio.to_thread(llm.reachable, llm.Backend.glimmer(url.value.strip(), model.value.strip()))
            result.value = w("reader.ok", names=", ".join(names))
        except Exception as ex:  # noqa: BLE001 - any failure means "not reachable"
            result.value = w("reader.ng", e=type(ex).__name__)
        page.update()

    def save(e):
        llm.set_reader(group.value, url.value.strip(), model.value.strip())
        page.pop_dialog()
        dialogs.say(w("reader.saved", name=w("reader." + llm.reader()) + " — " + llm.reader_name()))

    width = min(page.width or 360, 480) - 96
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(w("reader.title"), size=18),
        content=ft.Column([
            ft.Text(w("reader.help"), size=14),
            group, url, model,
            ft.OutlinedButton(w("reader.test"), on_click=check, height=48), result,
        ], tight=True, width=width, spacing=12),
        actions=[ft.TextButton(w("cancel"), on_click=lambda e: page.pop_dialog(), height=48),
                 ft.FilledButton(w("save"), on_click=save, height=48)],
        inset_padding=16,
    ))


def build(page: ft.Page, here: str | None, rebuild) -> Dialogs:
    """Lay out the views in the screen's language; `here` is this device's language."""
    lang = llm.language(here)
    w = Words(lang)
    dialogs = Dialogs(page, w)
    page.controls.clear()
    page.services[:] = [s for s in page.services if not isinstance(s, ft.FilePicker)]  # send_view and the voice buttons add their own
    read, refresh_read = read_view(page, dialogs, w, lang)
    land, refresh_land = land_view(page, dialogs, w, lang)
    nouns, refresh_nouns = nouns_view(page, dialogs, w)
    views = [(send_view(page, dialogs, w, lang), None), (read, refresh_read), (land, refresh_land), (nouns, refresh_nouns)]
    holder = ft.Container()

    def go(e=None):
        view, refresh = views[page.navigation_bar.selected_index]
        if refresh:
            refresh()
        holder.content = view
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[ft.NavigationBarDestination(icon=ft.Icons.PHOTO_CAMERA, label=w("nav.send")),
                      ft.NavigationBarDestination(icon=ft.Icons.VISIBILITY, label=w("nav.read")),
                      ft.NavigationBarDestination(icon=ft.Icons.TERRAIN, label=w("nav.land")),
                      ft.NavigationBarDestination(icon=ft.Icons.LABEL, label=w("nav.nouns"))],
        selected_index=0, on_change=go)
    page.appbar = ft.AppBar(title=ft.Text("fieldnotes"), actions=[
        ft.IconButton(ft.Icons.TRANSLATE, tooltip=w("tip.language"),
                      on_click=lambda e: ask_language(page, dialogs, here, rebuild)),
        ft.IconButton(ft.Icons.MEMORY, tooltip=w("tip.reader"), on_click=lambda e: ask_reader(page, dialogs)),
        ft.IconButton(ft.Icons.SETTINGS, tooltip=w("tip.consent"), on_click=lambda e: ask_consent(page, dialogs))]
        + ([ft.IconButton(ft.Icons.CAMERA_ALT_OUTLINED, tooltip=w("tip.capture"), on_click=lambda e: page.run_task(capture, page, dialogs))]
           if DEMO else []))
    page.add(holder)
    go()
    return dialogs


DEMO = os.environ.get("FIELDNOTES_DEMO") == "1"  # a capture button for the video (WP18 item 9)


async def capture(page: ft.Page, dialogs: Dialogs):
    """The page as it is now, as a 1280x720 PNG for the video, under <root>/video/frames/."""
    view = ["send", "read", "land", "nouns"][page.navigation_bar.selected_index]
    try:
        png = await page.take_screenshot()  # the device ratio: a ratio of 1 on a 2x screen draws a quarter of the page
        path = appdata.save_frame(png, ROOT / "video" / "frames", view)
    except Exception as ex:  # noqa: BLE001 - a failed capture is said, not raised
        dialogs.say(dialogs.w("capture.failed", e=f"{type(ex).__name__}: {ex}"))
        return
    dialogs.say(dialogs.w("capture.saved", path=str(path)))


async def main(page: ft.Page):
    page.title = "fieldnotes"
    page.enable_screenshots = DEMO
    page.theme_mode = ft.ThemeMode.DARK  # outdoors in the sun, dark reads best and saves the battery (WP18 item 6)
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    here = await device_language(page)

    def rebuild():
        """After the language changes: the same views, in the new words."""
        dialogs = build(page, here, rebuild)
        lang, w = llm.language_setting(), dialogs.w
        dialogs.say(w("lang.saved", lang=w("lang.saved_auto") if lang == llm.AUTO else llm.language_label(lang)))

    dialogs = build(page, here, rebuild)
    if llm.training_consent() is None:
        ask_consent(page, dialogs, first=True)


def run(host: str = "0.0.0.0", port: int = 8550):
    os.environ.setdefault("FLET_SECRET_KEY", secrets.token_hex(16))  # signs upload URLs
    UPLOADS.mkdir(exist_ok=True)
    for url in appdata.lan_urls(port):
        print(f"fieldnotes app: open {url} on the phone (same Wi-Fi or Tailscale)", flush=True)
        qr = appdata.qr_text(url)
        print(qr if qr else "  (no QR code here: the qrcode package is not installed; type the address)", flush=True)
    ft.run(main, host=host, port=port, view=ft.AppView.WEB_BROWSER, upload_dir=str(UPLOADS))


if __name__ == "__main__":
    run()
