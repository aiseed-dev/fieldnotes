"""The farmer's voice: transcribe (faked), sort, and file into the day's record."""

from __future__ import annotations

import io
import json
import wave

import numpy as np

from conftest import DAY, FIELD, add_photos
from fieldnotes import pipeline, voice
from fieldnotes.records import Record

SAID = "東側を刈って草マルチにした。ダイコンに本葉が出た。酸度は違う、スギナが少ない。"


def wav_bytes(rate=24_000, channels=1, seconds=0.2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(np.zeros(int(rate * seconds) * channels, dtype=np.int16).tobytes())
    return buf.getvalue()


def heard(calls):
    def transcriber(data, keywords, lang):
        calls.append((data, list(keywords), lang))
        return SAID
    return transcriber


def test_voice_after_a_reading(root, model, sam, wx, backend):
    add_photos(root)
    pipeline.run_observation(FIELD, DAY, root, backend)
    src = root / "uploads" / "rec.m4a"
    src.parent.mkdir()
    src.write_bytes(b"fake m4a")
    calls = []
    text, changed = voice.file_voice(src, FIELD, DAY, root, backend, transcriber=heard(calls))

    assert text == SAID and calls[0][0] == b"fake m4a" and calls[0][2] == "ja"
    assert "セイタカアワダチソウ" in calls[0][1] and "草マルチ" in calls[0][1]  # the field's names and farm words
    kept = list((root / "photos" / FIELD / DAY.isoformat()).glob("*-voice.m4a"))
    assert len(kept) == 1 and not src.exists()
    assert pipeline.photos_for(FIELD, DAY, root) == [p for p in pipeline.photos_for(FIELD, DAY, root) if p.endswith(".jpg")]

    rec = Record.load(root / "records", FIELD, DAY.isoformat())
    assert [(o.key, o.text) for o in rec.voice] == [
        ("work", "東側を刈って草マルチにした"), ("seen", "ダイコンに本葉が出た"), ("seen", "crops: right")]
    acidity = next(o for o in rec.observations if o.key == "acidity")
    assert (acidity.verdict, acidity.reason) == ("wrong", "スギナが少ないので酸性ではない")
    assert SAID in rec.farmer_note and kept[0].name in rec.farmer_note
    assert rec.note_model == voice.MODEL and rec.voice_model == "fake-model"
    assert len(changed) == 4
    # the AI lines and today's verdicts were in the sorting prompt
    prompt = model.messages["voice"][0][1]["content"]
    assert "acidity: pH ~5.5-6.5" in prompt and SAID in prompt


def test_voice_lines_survive_a_rerun_and_feed_the_reading(root, model, sam, wx, backend):
    add_photos(root)
    src = root / "rec.wav"
    src.write_bytes(wav_bytes())
    voice.file_voice(src, FIELD, DAY, root, backend, transcriber=heard([]))  # before any reading
    rec = Record.load(root / "records", FIELD, DAY.isoformat())
    assert rec.observations == [] and [o.key for o in rec.voice] == ["work", "seen", "seen", "seen"]

    pipeline.mark(FIELD, DAY, "seen#2", "wrong", "AI の取り違え", root=root)  # "acidity: wrong (...)"
    pipeline.run_observation(FIELD, DAY, root, backend)
    rec = Record.load(root / "records", FIELD, DAY.isoformat())
    assert len(rec.voice) == 4 and rec.voice[2].verdict == "wrong" and SAID in rec.farmer_note
    assert rec.voice[2].text == "acidity: wrong (スギナが少ないので酸性ではない)"
    read = [p["text"] for p in model.messages["describe"][-1][1]["content"] if p["type"] == "text"]
    told = next(t for t in read if t.startswith("The farmer said"))
    assert "work: 東側を刈って草マルチにした" in told and "crops: right" in told and "acidity" not in told


def test_record_round_trip_with_voice():
    rec = Record(FIELD, DAY.isoformat(), ai_model="x", voice=[voice.Observation("work", "刈った", "right")], voice_model="m",
                 note_model=voice.MODEL, note_language="ja", farmer_note="08:00 刈った (080000-voice.m4a)")
    assert Record.from_markdown(rec.to_markdown()) == rec


def test_transcribe_request(monkeypatch):
    sent = {}

    class Reply:
        status_code = 200

        def json(self):
            return {"sessionId": "s", "transcript": " 刈った ", "audioDurationMs": 200, "turns": []}

    def post(url, headers, files, timeout):
        sent.update(url=url, auth=headers["Authorization"], request=json.loads(files["request"][1]),
                    audio=files["audio"][1])
        return Reply()

    monkeypatch.setattr(voice.httpx, "post", post)
    data = wav_bytes()
    assert voice.transcribe(data, ["オギ"], "ja") == "刈った"
    assert sent["url"] == "https://api.meta.ai/v1/asr/transcribe" and sent["auth"] == "Bearer test-key"
    assert sent["request"] == {"model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV", "mode": "PUSH_TO_TALK",
                               "keywords": ["オギ"], "languageBias": ["Japanese"]}
    assert sent["audio"] == data  # a 24 kHz mono WAV goes as it is


def test_bias_and_conversion():
    assert voice.bias("zh") == ["Mandarin Chinese"] and voice.bias("en") == ["English"] and voice.bias("xx") == []
    stereo = wav_bytes(rate=44_100, channels=2)
    out = voice.to_wav(stereo)
    with wave.open(io.BytesIO(out)) as f:
        assert (f.getnchannels(), f.getsampwidth(), f.getframerate()) == (1, 2, 24_000)
        assert abs(f.getnframes() - 4_800) < 600
