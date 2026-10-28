"""Model backends and small helpers shared by describe and plants.

Muse Spark on api.meta.ai and Muse Glimmer on the MS-S1 MAX (Ollama) both
speak the OpenAI Chat Completions format, so the same code serves both; only
`base_url` and `model` differ.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI


SPARK = "muse-spark-1.3"
SPARK_CONTRIBUTOR = "muse-spark-1.3-contributor"  # cheaper; Meta may train on what is sent


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "fieldnotes"


def api_key() -> str:
    """The Meta Model API key: $MODEL_API_KEY if set, else the file
    $XDG_CONFIG_HOME/fieldnotes/model_api_key (default ~/.config/...),
    which should be readable only by the user (chmod 600)."""
    if os.environ.get("MODEL_API_KEY"):
        return os.environ["MODEL_API_KEY"]
    p = config_dir() / "model_api_key"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    raise RuntimeError(f"no Meta Model API key: set MODEL_API_KEY or write it to {p}")


def training_consent() -> bool | None:
    """Whether the farmer agreed that what Muse Spark is sent (photos, records)
    may be used by Meta for training, in return for the cheaper contributor
    model. None until asked; the app asks on first launch."""
    p = config_dir() / "settings.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("training_consent")


def set_training_consent(agreed: bool) -> None:
    p = config_dir() / "settings.json"
    settings = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    settings["training_consent"] = bool(agreed)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings, ensure_ascii=False, indent=1), encoding="utf-8")


@dataclass
class Backend:
    name: str
    base_url: str
    model: str
    api_key: str

    @classmethod
    def spark(cls) -> "Backend":
        """Standard Muse Spark, or the contributor model only if the farmer agreed."""
        model = SPARK_CONTRIBUTOR if training_consent() else SPARK
        return cls(model, "https://api.meta.ai/v1", model, api_key())

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
