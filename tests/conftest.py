"""Offline fakes: no test here may reach the Meta API, Open-Meteo or the GSI tile server."""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import date

import numpy as np
import pytest
from PIL import Image

from fieldnotes import concepts, describe, llm, plants, propose, segment, surroundings, weather
from fieldnotes.llm import Backend
from fieldnotes.segment import ConceptResult, Instance, SegmentResult

DAY = date(2026, 10, 28)
FIELD = "uncut"
SCI = re.compile(r"\(([A-Z][a-z]+ [a-z][a-z-]+)\)")


class FakeModel:
    """Stands in for every `chat` call; answers by which system prompt it gets.

    `reading` is what Muse Spark says about a field; tests change it to
    simulate a second, different reading of the same day.
    """

    def __init__(self):
        self.calls: list[str] = []
        self.messages: dict[str, list[list[dict]]] = {}
        self.reading = [
            {"key": "overall", "text": "Even green cover, goldenrod leading.", "confidence": 0.8},
            {"key": "dominant", "plants": [{"name": "セイタカアワダチソウ", "scientific": "Solidago altissima",
                                             "share": "~40%"}], "confidence": 0.7},
            {"key": "acidity", "level": "5.5-6.5", "direction": "none", "evidence": "goldenrod", "confidence": 0.5},
            {"key": "animal", "text": "no new tracks", "confidence": 0.6},
        ]

    def __call__(self, backend, messages):
        system, user = messages[0]["content"], messages[1]["content"]
        text = user if isinstance(user, str) else "\n".join(p["text"] for p in user if p["type"] == "text")
        kinds = {concepts.SYSTEM: "concepts", plants.ECOLOGY_SYSTEM: "ecology", describe.SYSTEM: "describe",
                 describe.COMPARE_SYSTEM: "compare", propose.SYSTEM: "propose",
                 surroundings.SYSTEM: "surroundings"}
        # prompts may carry a trailing language rule (llm.in_language)
        kind = next(k for s, k in kinds.items() if system.startswith(s))
        self.calls.append(kind)
        self.messages.setdefault(kind, []).append(messages)
        if kind == "concepts":
            return json.dumps([{"scientific": s, "noun": "goldenrod", "confidence": 0.6}
                               for s in SCI.findall(text)])
        if kind == "ecology":
            sci = SCI.search(text).group(1)
            return json.dumps({"name": "セイタカアワダチソウ", "scientific": sci,
                               "notes": [{"aspect": "soil_ph", "text": "tolerates acid soil", "confidence": 0.5}]})
        if kind == "describe":
            return json.dumps(self.reading)
        if kind == "compare":
            names = re.findall(r"--- FIELD (\S+)", text)
            return json.dumps([
                {"key": "overall", "text": "The fields differ in height.", "confidence": 0.7},
                {"key": "fertility", "order": names, "levels": dict.fromkeys(names, "moderate"),
                 "evidence": "growth", "confidence": 0.5}])
        if kind == "propose":
            return json.dumps({"summary": {"text": "A legume-led mix.", "confidence": 0.6},
                               "mix": [{"name": "クリムソンクローバー", "scientific": "Trifolium incarnatum",
                                        "role": "nitrogen", "share": "~30%", "why": "low nitrogen",
                                        "confidence": 0.6}],
                               "sowing": {"text": "sow in November", "confidence": 0.5},
                               "cautions": [], "watch": [{"text": "clover leaves by December"}]})
        return json.dumps([{"aspect": "land_use", "text": "paddies to the south", "confidence": 0.6}])


class FakeSam:
    """segment_concepts without the API: goldenrod covers the left half, bare soil the top quarter."""

    def __init__(self):
        self.calls: list[tuple[str, list[str]]] = []

    def __call__(self, photo, nouns, max_side=2048):
        self.calls.append((photo.name, list(nouns)))
        with Image.open(photo) as im:
            w, h = im.size
        found = {}
        for noun in nouns:
            union = np.zeros((h, w), dtype=np.uint8)
            if noun == "goldenrod":
                union[:, : w // 2] = 1
            elif noun == "bare soil":
                union[: h // 4, :] = 1
            inst = [Instance(1, (0, 0, w, h), int(union.sum()), 0.9)] if union.any() else []
            found[noun] = ConceptResult(noun, w, h, inst, union)
        return SegmentResult(photo, w, h, found)


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """Work in an empty folder, with a dummy key, and fail loudly on any network use."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_API_KEY", "test-key")
    monkeypatch.setenv("FIELDNOTES_ROOT", str(tmp_path))

    def no_network(*a, **k):
        raise AssertionError("network used in an offline test")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(llm, "OpenAI", no_network)
    monkeypatch.setattr(segment, "AsyncOpenAI", no_network)


@pytest.fixture
def model(monkeypatch):
    fake = FakeModel()
    for mod in (llm, describe, concepts, plants, propose, surroundings):
        monkeypatch.setattr(mod, "chat", fake)
    return fake


@pytest.fixture
def sam(monkeypatch):
    fake = FakeSam()
    monkeypatch.setattr(segment, "segment_concepts", fake)  # concepts.segment_field imports it at call time
    return fake


@pytest.fixture
def wx(monkeypatch):
    def daily_weather(d, root=None, lookback=30):
        return {"tmax": 25.1, "tmin": 15.4, "rain_mm": 2.0, "days_since_rain": 1}

    monkeypatch.setattr(weather, "daily_weather", daily_weather)


@pytest.fixture
def backend():
    return Backend("fake-model", "http://unused", "fake", "k")


@pytest.fixture
def root(tmp_path):
    return tmp_path


def add_photos(root, field=FIELD, day=DAY, names=("080000-a", "081500-b"), size=(64, 48)):
    d = root / "photos" / field / day.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(names):
        Image.new("RGB", size, (30 * i + 40, 120, 60)).save(d / f"{n}.jpg", quality=80)
    return d
