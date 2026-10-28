"""Model backends and small helpers shared by describe and plants.

Muse Spark on api.meta.ai and Muse Glimmer on the MS-S1 MAX (Ollama) both
speak the OpenAI Chat Completions format, so the same code serves both; only
`base_url` and `model` differ.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class Backend:
    name: str
    base_url: str
    model: str
    api_key: str

    @classmethod
    def spark(cls) -> "Backend":
        return cls("muse-spark-1.3", "https://api.meta.ai/v1", "muse-spark-1.3", os.environ["MODEL_API_KEY"])

    @classmethod
    def glimmer(cls, host: str = "192.168.100.6", model: str = "muse-glimmer") -> "Backend":
        return cls(f"muse-glimmer@{host}", f"http://{host}:11434/v1", model, "ollama")


def chat(backend: Backend, messages: list[dict]) -> str:
    client = OpenAI(base_url=backend.base_url, api_key=backend.api_key)
    resp = client.chat.completions.create(model=backend.model, messages=messages, temperature=0.2)
    return resp.choices[0].message.content or ""


def json_value(text: str):
    """Accept bare JSON or JSON wrapped in a ```json fence."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("\n") + 1:] if t.lower().startswith("json") else t
    return json.loads(t)


def conf(it: dict) -> str:
    c = it.get("confidence")
    return "" if c is None else f" [{float(c):.2f}]"
