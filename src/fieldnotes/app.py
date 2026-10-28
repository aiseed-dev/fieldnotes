"""Phone app: send field photos from an iPhone or Android browser.

Run on the house machine:

    .venv/bin/python -m fieldnotes.app            # http://<host>:8550

and open it on the phone (at home over Wi-Fi, in the field through
Tailscale). Pick the field, take or choose photos, send. Each photo lands in
photos/<field>/<date>/ (see inbox.py); no folder work by hand.

Three views, switched from the bar at the bottom (docs/design.md §1.13):
送る / Send (this file's send_view), 読む / Read (run the pipeline, see the SAM
overlays and the AI's lines, mark each right or wrong) and 名詞 / Nouns (the
SAM noun phrases of a field, marked right or wrong with a replacement).

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

from . import appdata, concepts, llm, pipeline
from .inbox import AROUND, file_photo, list_fields, valid_field
from .records import Observation, Record
from .ui import Words

ROOT = Path(os.environ.get("FIELDNOTES_ROOT", ".")).resolve()
PHOTOS = ROOT / "photos"
RECORDS = ROOT / "records"
UPLOADS = ROOT / "uploads"
NEW = "__new__"


def send_view(page: ft.Page, w: Words) -> ft.Control:
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
    day = ft.TextField(label=w("send.day"), value=date.today().isoformat())
    status = ft.Text("")
    progress = ft.ProgressBar(value=0, visible=False)
    sent = ft.Column(spacing=4)

    def on_field_change(e):
        new_field.visible = field_dd.value == NEW
        page.update()

    field_dd.on_select = on_field_change

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
        progress.value = batch["done"] / batch["total"]
        try:
            dest = file_photo(UPLOADS / batch["dir"] / e.file_name, batch["field"], batch["day"], PHOTOS)
            sent.controls.insert(0, ft.Text(f"✓ {dest.relative_to(ROOT)}", size=13))
        except Exception as ex:  # one bad file should not stop the rest
            sent.controls.insert(0, ft.Text(f"✗ {e.file_name}: {ex}", size=13, color=ft.Colors.ERROR))
        if batch["done"] == batch["total"]:
            status.value = w("send.placed", n=batch["total"], field=appdata.place_label(batch["field"], w))
            progress.visible = False
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
        batch.update(dir=sub, field=field, day=d, total=len(files), done=0)
        progress.value, progress.visible = 0, True
        status.value = w("send.sending", n=len(files))
        page.update()
        await picker.upload(files=[
            ft.FilePickerUploadFile(id=f.id, name=f.name, upload_url=page.get_upload_url(f"{sub}/{f.name}", 600))
            for f in files
        ])

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
    ])

THUMB = 164  # two thumbnails side by side in 375 px minus the 16 px page padding
GOOD, BAD = ft.Colors.GREEN_700, ft.Colors.RED_700


def verdict_row(w: Words, current: str | None, on_right, on_wrong) -> ft.Row:
    """✓ / ✗ as two large buttons; the one matching `current` is filled."""
    def button(label: str, color, picked: bool, on_click):
        cls = ft.FilledButton if picked else ft.OutlinedButton
        kw = {"style": ft.ButtonStyle(bgcolor=color, color=ft.Colors.WHITE)} if picked else {"style": ft.ButtonStyle(color=color)}
        return cls(label, on_click=on_click, expand=True, height=48, **kw)

    return ft.Row([button(w("right"), GOOD, current == "right", on_right),
                   button(w("wrong"), BAD, current == "wrong", on_wrong)], spacing=8)


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


def card(*controls: ft.Control) -> ft.Container:
    return ft.Container(ft.Column(list(controls), spacing=8), padding=12, border_radius=8,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT))


def read_view(page: ft.Page, dialogs: Dialogs, w: Words, lang: str | None):
    """読む: run the pipeline on a field and day, then show the SAM overlays and the
    AI's lines, each with ✓ / ✗ saved through pipeline.mark. Returns (view, refresh)."""
    field_dd = ft.Dropdown(label=w("field"), expand=True)
    day_dd = ft.Dropdown(label=w("read.day"), expand=True)
    read_btn = ft.FilledButton(w("read.button"), icon=ft.Icons.VISIBILITY, height=56, expand=True)
    busy = ft.Row([ft.ProgressRing(width=24, height=24), ft.Text("", expand=True)], visible=False, spacing=12)
    status = ft.Text("")
    photos = ft.Column(spacing=8)
    lines = ft.Column(spacing=10)
    running = {"on": False}

    def chosen() -> tuple[str, str] | None:
        return (field_dd.value, day_dd.value) if field_dd.value and day_dd.value else None

    def refresh(e=None):
        """Re-scan photos/ (the 送る view may have added some) and redraw."""
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
        """Photos (with overlays once read) and the record's lines for the chosen field and day."""
        photos.controls.clear()
        lines.controls.clear()
        sel = chosen()
        if sel:
            field, day = sel
            originals = appdata.day_photos(PHOTOS, field, day)
            overlays = appdata.overlay_paths(RECORDS, field, day)
            tiles = []
            for i, p in enumerate(originals):
                shown, what = (overlays[i], "SAM") if i < len(overlays) else (p, w("read.photo"))
                tiles.append(ft.Container(
                    ft.Image(src=appdata.shrunk_jpeg(shown, 480), width=THUMB, height=THUMB * 3 // 4, fit=ft.BoxFit.COVER,
                             border_radius=6),
                    on_click=lambda e, shown=shown, i=i, what=what: dialogs.photo(shown, f"{what} {i + 1}/{len(originals)}"),
                    tooltip=w("read.tap")))
            note = w("read.with_sam") if overlays else w("read.not_yet")
            photos.controls += [ft.Text(w("read.photos", n=len(originals), note=note), size=14), ft.Row(tiles, wrap=True, spacing=8, run_spacing=8)]
            show_lines()
        page.update()

    def show_lines():
        lines.controls.clear()
        field, day = chosen()
        path = Record.path_for(RECORDS, field, day)
        if not path.exists():
            return
        try:
            rec = Record.load(RECORDS, field, day)
        except Exception as ex:
            lines.controls.append(ft.Text(w("read.bad_record", e=ex), color=ft.Colors.ERROR))
            return
        lines.controls.append(ft.Text(w("read.question"), size=18, weight=ft.FontWeight.BOLD))
        seen: dict[str, int] = {}
        cards = []
        for o in rec.observations:
            seen[o.key] = seen.get(o.key, 0) + 1
            # pipeline.mark finds a repeated key as key#n
            cards.append(line_card(o, o.key if seen[o.key] == 1 else f"{o.key}#{seen[o.key]}"))
        lines.controls += cards or [ft.Text(w("read.empty"))]
        if rec.farmer_note:
            lines.controls.append(card(ft.Text(w("read.note"), size=13), ft.Text(rec.farmer_note, selectable=True)))

    def line_card(o: Observation, ref: str) -> ft.Container:
        field, day = chosen()
        text, conf = appdata.split_conf(o.text)
        head = appdata.key_label(o.key, w) + ("　" + w("read.confidence", c=conf) if conf else "")
        body = [ft.Text(head, size=13, color=ft.Colors.ON_SURFACE_VARIANT), ft.Text(text, size=16, selectable=True)]
        if o.verdict == "wrong" and o.reason:
            body.append(ft.Text(w("read.reason", r=o.reason), size=14, color=BAD))

        def save(verdict: str, reason: str | None = None):
            try:
                pipeline.mark(field, date.fromisoformat(day), ref, verdict, reason or None, root=ROOT)
            except Exception as ex:
                dialogs.say(w("not_saved", e=ex), error=True)
                return
            show_lines()  # redraw from the file: what was saved is what is shown
            page.update()

        def ask_reason(e):
            reason = ft.TextField(label=w("what_wrong"), value=o.reason or "", multiline=True,
                                  min_lines=2, max_lines=5, autofocus=True)
            dialogs.form(w("wrong_title", what=appdata.key_label(o.key, w)), [reason], lambda: save("wrong", reason.value.strip()))

        return card(*body, verdict_row(w, o.verdict, lambda e: save("right"), ask_reason))

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
        ft.Text(w("read.title"), size=22, weight=ft.FontWeight.BOLD),
        ft.Row([field_dd]), ft.Row([day_dd]),
        ft.Row([read_btn]), busy, status, photos, lines,
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
        dialogs.say(w("reader.saved", name=w("reader." + llm.reader())))

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
    page.services[:] = [s for s in page.services if not isinstance(s, ft.FilePicker)]  # send_view adds its own
    read, refresh_read = read_view(page, dialogs, w, lang)
    nouns, refresh_nouns = nouns_view(page, dialogs, w)
    views = [(send_view(page, w), None), (read, refresh_read), (nouns, refresh_nouns)]
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
                      ft.NavigationBarDestination(icon=ft.Icons.LABEL, label=w("nav.nouns"))],
        selected_index=0, on_change=go)
    page.appbar = ft.AppBar(title=ft.Text("fieldnotes"), actions=[
        ft.IconButton(ft.Icons.TRANSLATE, tooltip=w("tip.language"),
                      on_click=lambda e: ask_language(page, dialogs, here, rebuild)),
        ft.IconButton(ft.Icons.MEMORY, tooltip=w("tip.reader"), on_click=lambda e: ask_reader(page, dialogs)),
        ft.IconButton(ft.Icons.SETTINGS, tooltip=w("tip.consent"), on_click=lambda e: ask_consent(page, dialogs))])
    page.add(holder)
    go()
    return dialogs


async def main(page: ft.Page):
    page.title = "fieldnotes"
    page.theme_mode = ft.ThemeMode.SYSTEM
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
    ft.run(main, host=host, port=port, view=ft.AppView.WEB_BROWSER, upload_dir=str(UPLOADS))


if __name__ == "__main__":
    run()
