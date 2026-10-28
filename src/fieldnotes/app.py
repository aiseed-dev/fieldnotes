"""Phone app: send field photos from an iPhone or Android browser.

Run on the house machine:

    .venv/bin/python -m fieldnotes.app            # http://<host>:8550

and open it on the phone (at home over Wi-Fi, in the field through
Tailscale). Pick the field, take or choose photos, send. Each photo lands in
photos/<field>/<date>/ (see inbox.py); no folder work by hand.

This is step 1 of the app in docs/design.md §1.13; reading the field and the
farmer's right/wrong come next.
"""

from __future__ import annotations

import os
import secrets
from datetime import date
from pathlib import Path

import flet as ft

from .inbox import file_photo, list_fields, valid_field

ROOT = Path(os.environ.get("FIELDNOTES_ROOT", ".")).resolve()
PHOTOS = ROOT / "photos"
RECORDS = ROOT / "records"
UPLOADS = ROOT / "uploads"
NEW = "__new__"


def main(page: ft.Page):
    page.title = "fieldnotes"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    fields = list_fields(PHOTOS, RECORDS)
    field_dd = ft.Dropdown(
        label="畑",
        options=[ft.DropdownOption(key=f, text=f) for f in fields] + [ft.DropdownOption(key=NEW, text="＋ 新しい畑")],
        value=fields[0] if fields else NEW,
        expand=True,
    )
    new_field = ft.TextField(label="新しい畑の名前（英小文字・数字・ハイフン）", visible=not fields)
    day = ft.TextField(label="日付（写真に撮影日があればそちらを使う）", value=date.today().isoformat())
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
        return name if name and valid_field(name) else None

    def chosen_day() -> date | None:
        try:
            return date.fromisoformat((day.value or "").strip())
        except ValueError:
            return None

    def on_upload(e: ft.FilePickerUploadEvent):
        if e.error:
            status.value = f"送信に失敗: {e.file_name}: {e.error}"
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
            status.value = f"{batch['total']} 枚を {batch['field']} に置きました"
            progress.visible = False
        page.update()

    picker = ft.FilePicker(on_upload=on_upload)
    page.services.append(picker)

    async def pick_and_send(e):
        field, d = chosen_field(), chosen_day()
        if not field:
            status.value = "畑の名前を確かめてください（英小文字・数字・ハイフン）"
            page.update()
            return
        if not d:
            status.value = "日付は 2026-10-28 の形で"
            page.update()
            return
        files = await picker.pick_files(file_type=ft.FilePickerFileType.IMAGE, allow_multiple=True,
                                        cancel_upload_on_window_blur=False)
        if not files:
            return
        sub = secrets.token_hex(4)
        batch.update(dir=sub, field=field, day=d, total=len(files), done=0)
        progress.value, progress.visible = 0, True
        status.value = f"{len(files)} 枚を送っています…"
        page.update()
        await picker.upload(files=[
            ft.FilePickerUploadFile(id=f.id, name=f.name, upload_url=page.get_upload_url(f"{sub}/{f.name}", 600))
            for f in files
        ])

    page.add(
        ft.Text("畑の写真を送る", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([field_dd]),
        new_field,
        day,
        ft.FilledButton("撮る・選んで送る", icon=ft.Icons.PHOTO_CAMERA, on_click=pick_and_send,
                        style=ft.ButtonStyle(padding=20), expand=True),
        progress,
        status,
        sent,
    )


def run(host: str = "0.0.0.0", port: int = 8550):
    os.environ.setdefault("FLET_SECRET_KEY", secrets.token_hex(16))  # signs upload URLs
    UPLOADS.mkdir(exist_ok=True)
    ft.run(main, host=host, port=port, view=ft.AppView.WEB_BROWSER, upload_dir=str(UPLOADS))


if __name__ == "__main__":
    run()
