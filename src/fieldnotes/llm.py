"""Model backends and small helpers shared by describe and plants.

Muse Spark on api.meta.ai and Muse Glimmer on the MS-S1 MAX (llama-server)
both speak the OpenAI Chat Completions format, so the same code serves both;
only `base_url` and `model` differ. Which one reads the field is a setting
(`reader` in settings.json), changed from the app or `fieldnotes reader`.
SAM always runs on api.meta.ai.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI


SPARK = "muse-spark-1.3"
SPARK_CONTRIBUTOR = "muse-spark-1.3-contributor"  # cheaper; Meta may train on what is sent
GLIMMER_URL = "http://192.168.100.6:11434/v1"  # llama-server on the MS-S1 MAX
GLIMMER_MODEL = "muse-glimmer-30B"              # the server's alias (-a)
READERS = {"spark": "Muse Spark（api.meta.ai）", "glimmer": "Muse Glimmer（自宅のマシン）"}


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


def settings() -> dict:
    p = config_dir() / "settings.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def update_settings(**values) -> None:
    """Change some settings and keep the rest."""
    p = config_dir() / "settings.json"
    s = settings() | values
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def training_consent() -> bool | None:
    """Whether the farmer agreed that what Muse Spark is sent (photos, records)
    may be used by Meta for training, in return for the cheaper contributor
    model. None until asked; the app asks on first launch."""
    return settings().get("training_consent")


LANGUAGES = {"ja": "Japanese", "en": "English"}


def language() -> str:
    """The language the farmer reads: "ja" unless settings.json says otherwise."""
    lang = settings().get("language", "ja")
    return lang if lang in LANGUAGES else "ja"


def in_language(system: str) -> str:
    """A system prompt plus the rule to write every free-text value in the
    farmer's language. JSON keys, enum values and scientific names stay as
    they are, so parsing does not change."""
    return (system + f"\nWrite every free-text value (text, evidence, why, notes) in {LANGUAGES[language()]}. "
            "Keep JSON keys, the allowed enum values and scientific names exactly as specified.")


def set_training_consent(agreed: bool) -> None:
    update_settings(training_consent=bool(agreed))


def reader() -> str:
    """Which model reads the field: "spark" (default) or "glimmer"."""
    r = settings().get("reader", "spark")
    return r if r in READERS else "spark"


def glimmer_url() -> str:
    return settings().get("glimmer_url") or GLIMMER_URL


def glimmer_model() -> str:
    return settings().get("glimmer_model") or GLIMMER_MODEL


def set_reader(name: str, url: str | None = None, model: str | None = None) -> None:
    if name not in READERS:
        raise ValueError(f"reader must be one of {', '.join(READERS)}, not {name!r}")
    values = {"reader": name}
    if url:
        values["glimmer_url"] = url.rstrip("/")
    if model:
        values["glimmer_model"] = model
    update_settings(**values)


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
    def glimmer(cls, url: str | None = None, model: str | None = None) -> "Backend":
        """Muse Glimmer on a llama-server in the house (no key needed on the LAN)."""
        url, model = url or glimmer_url(), model or glimmer_model()
        host = url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        return cls(f"{model}@{host}", url, model, "none")

    @classmethod
    def default(cls) -> "Backend":
        """The reader the farmer chose in the settings."""
        return cls.glimmer() if reader() == "glimmer" else cls.spark()


def reachable(backend: Backend, timeout: float = 5) -> list[str]:
    """The model names the server offers; raises when it cannot be reached."""
    client = OpenAI(base_url=backend.base_url, api_key=backend.api_key, timeout=timeout, max_retries=0)
    return [m.id for m in client.models.list()]


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
