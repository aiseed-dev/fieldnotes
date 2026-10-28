"""The farmer's voice: a recording from the field, written down and sorted.

The farmer does not type. In the field they take photos and say what they did
and what they see; looking at a reading they say which lines are right or
wrong and why. One recording per call:

1. the file the phone gives (m4a, 3gp, ogg, webm or WAV) is kept as it is,
   as photos/<field>/<date>/<HHMMSS>-voice.<ext>, next to the photos;
2. Muse Voice Transcribe writes it down (converted to 24 kHz mono WAV first),
   biased to the farmer's language and to the names in this field;
3. Muse Spark sorts what was said into
   * `work`: something the farmer did (cut, sowed, mulched, harvested ...),
   * `seen`: something the farmer saw,
   * a verdict on one of the day's AI lines, with the reason;
4. the transcript goes under the record's "Farmer note", work and seen lines
   under "From the farmer's voice", and each verdict onto its AI line.

The sorting is the AI's reading of the farmer's words, so its lines can be
marked right or wrong like any other; the transcript and the recording stay
as they were said.
"""

from __future__ import annotations

import io
import json
import wave
from datetime import date, datetime
from pathlib import Path

import httpx

from . import concepts
from .inbox import photo_place
from .llm import LANGUAGES, Backend, api_key, chat, in_language, json_value, language
from .plants import species_in
from .records import Observation, Record, previous_records
from .ui import words

MODEL = "muse-voice-transcribe-1.0"
URL = "https://api.meta.ai/v1/asr/transcribe"
RATE = 24_000  # the model's native rate (dev.meta.ai: Speech to text)
AUDIO_SUFFIXES = {".wav", ".m4a", ".mp4", ".aac", ".3gp", ".amr", ".ogg", ".oga", ".opus", ".webm", ".mp3", ".flac"}
KINDS = ("work", "seen")

# languageBias takes language names from this list (dev.meta.ai: Speech to text)
SUPPORTED = {"Arabic", "Bengali", "Dutch", "English", "French", "German", "Hebrew", "Hindi", "Indonesian",
             "Italian", "Japanese", "Kannada", "Korean", "Malay", "Mandarin Chinese", "Marathi", "Polish",
             "Portuguese", "Spanish", "Tagalog", "Tamil", "Telugu", "Thai", "Turkish", "Vietnamese"}


def bias(code: str) -> list[str]:
    """languageBias for a language code; empty (the model detects) when not supported."""
    name = "Mandarin Chinese" if code == "zh" else LANGUAGES.get(code, ("",))[0]
    return [name] if name in SUPPORTED else []


# ---- audio ---------------------------------------------------------------

def _wav_ok(data: bytes) -> bool:
    try:
        with wave.open(io.BytesIO(data)) as f:
            return f.getnchannels() == 1 and f.getsampwidth() == 2 and f.getframerate() in (16_000, 24_000)
    except (wave.Error, EOFError):
        return False


def to_wav(data: bytes) -> bytes:
    """Any recording the phone gives -> mono 16-bit PCM WAV at 24 kHz (a WAV
    that is already mono 16-bit at 16 or 24 kHz is sent as it is)."""
    if _wav_ok(data):
        return data
    import av  # PyAV: decodes m4a/aac/3gp/ogg/webm without an ffmpeg binary

    pcm = bytearray()
    with av.open(io.BytesIO(data)) as box:
        stream = next(s for s in box.streams if s.type == "audio")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=RATE)
        for frame in box.decode(stream):
            for out in resampler.resample(frame):
                pcm += out.to_ndarray().tobytes()
        for out in resampler.resample(None):
            pcm += out.to_ndarray().tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(bytes(pcm))
    return buf.getvalue()


def transcribe(data: bytes, keywords: list[str] = (), lang: str | None = None) -> str:
    """The recording, written down by Muse Voice Transcribe (one turn, PUSH_TO_TALK)."""
    request = {"model": MODEL, "audioEncoding": "WAV", "mode": "PUSH_TO_TALK"}
    if keywords:
        request["keywords"] = list(keywords)
    if b := bias(lang or language()):
        request["languageBias"] = b
    r = httpx.post(URL, headers={"Authorization": f"Bearer {api_key()}", "Accept": "application/json"},
                   files={"request": (None, json.dumps(request, ensure_ascii=False), "application/json"),
                          "audio": ("voice.wav", to_wav(data), "audio/wav")},
                   timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"Muse Voice Transcribe: HTTP {r.status_code} {r.text[:200]}")
    return r.json()["transcript"].strip()


def vocabulary(field: str, records_root: Path) -> list[str]:
    """Words to bias the transcript toward: the plants this field's readings
    named, the SAM targets, and the farm words of the farmer's language."""
    names: list[str] = []
    for rec in previous_records(records_root, field, "9999", n=3):
        for name, sci in species_in(rec.observations):
            names += [name, sci]
    for c in concepts.FieldConcepts.load(records_root, field).items:
        if c.by != "default":
            names.append(c.target.split(" (")[0])
    names += [x.strip() for x in words()("voice.words").split(",")]
    return [n for n in dict.fromkeys(n for n in names if n)][:60]


# ---- sorting what was said ----------------------------------------------

SYSTEM = """A farmer on a natural-farming field recorded what they said, and it was written down.
Sort what they said into items. Each item is one of:
- {"kind": "work", "text": "..."}: something the farmer did or had done on this field (cut, sowed, mulched, watered, harvested, pulled, planted), with where and how if they said so.
- {"kind": "seen", "text": "..."}: something the farmer saw, smelled or noticed.
- {"kind": "verdict", "line": "<ref>", "verdict": "right" | "wrong", "reason": "..."}: the farmer said one of today's AI lines (listed below with their ref) is right or wrong. Use only refs from the list. The reason is why, in the farmer's words; empty when they gave none.
Keep the farmer's meaning and words; do not add anything they did not say. Leave out filler and false starts.
Answer with a JSON array of items only."""


def line_refs(rec: Record | None) -> list[tuple[str, Observation]]:
    """(ref, line) for each AI line, ref as pipeline.mark takes it (key, key#2 ...)."""
    out, seen = [], {}
    for o in rec.observations if rec else []:
        seen[o.key] = seen.get(o.key, 0) + 1
        out.append((o.key if seen[o.key] == 1 else f"{o.key}#{seen[o.key]}", o))
    return out


def build_messages(transcript: str, rec: Record | None) -> list[dict]:
    refs = line_refs(rec)
    listed = "\n".join(f"{ref}: {o.text}" for ref, o in refs) or "(no AI lines yet today)"
    return [{"role": "system", "content": in_language(SYSTEM)},
            {"role": "user", "content": f"Today's AI lines:\n{listed}\n\nWhat the farmer said:\n{transcript}\n\nJSON array only."}]


def sort_speech(transcript: str, rec: Record | None, backend: Backend) -> list[dict]:
    items = json_value(chat(backend, build_messages(transcript, rec)))
    return [it for it in items if isinstance(it, dict)]


# ---- one recording into the record --------------------------------------

def _one_line(text) -> str:
    return " ".join(str(text or "").split())


def apply(rec: Record, items: list[dict], model: str) -> list[Observation]:
    """Put sorted items into `rec`; returns what changed (new voice lines and marked AI lines).
    A verdict on a line that is not there is kept as something the farmer saw."""
    refs = dict(line_refs(rec))
    changed = []
    for it in items:
        kind = it.get("kind")
        if kind == "verdict" and it.get("line") in refs and it.get("verdict") in ("right", "wrong"):
            o = refs[it["line"]]
            o.verdict = it["verdict"]
            o.reason = (_one_line(it.get("reason")) or None) if o.verdict == "wrong" else None
            changed.append(o)
            continue
        if kind == "verdict":
            reason = _one_line(it.get("reason"))
            kind, it = "seen", {"text": f'{it.get("line", "")}: {it.get("verdict", "")}' + (f" ({reason})" if reason else "")}
        if kind in KINDS and _one_line(it.get("text")):
            o = Observation(kind, _one_line(it["text"]))
            rec.voice.append(o)
            changed.append(o)
    if changed:
        rec.voice_model = model
    return changed


def file_voice(src: Path, field: str, day: date, root: Path, backend: Backend | None = None, *,
               transcriber=transcribe) -> tuple[str, list[Observation]]:
    """Keep the recording next to the day's photos, write it down, sort it into
    the day's record. Returns (transcript, what changed)."""
    if not photo_place(field):
        raise ValueError(f"bad field name {field!r}")
    suffix = src.suffix.lower() if src.suffix.lower() in AUDIO_SUFFIXES else ".m4a"
    data = src.read_bytes()
    now = datetime.now()
    dest_dir = root / "photos" / field / day.isoformat()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{now:%H%M%S}-voice{suffix}"
    n = 1
    while dest.exists():
        n += 1
        dest = dest_dir / f"{now:%H%M%S}-voice-{n}{suffix}"
    src.replace(dest)

    records = root / "records"
    text = transcriber(data, vocabulary(field, records), language())
    path = Record.path_for(records, field, day.isoformat())
    rec = Record.load(records, field, day.isoformat()) if path.exists() else Record(field=field, date=day.isoformat())
    rec.farmer_note = "\n".join(x for x in (rec.farmer_note, f"{now:%H:%M} {_one_line(text)} ({dest.name})") if x)
    rec.note_model, rec.note_language = MODEL, rec.note_language or language()
    changed = []
    if text:
        backend = backend or Backend.default()
        changed = apply(rec, sort_speech(text, rec, backend), backend.name)
    rec.save(records)
    return text, changed
