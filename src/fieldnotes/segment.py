"""Segment a field photo with SAM 3.1 and turn the masks into coverage numbers.

SAM 3.1 takes ONE short noun phrase per request and returns a box + mask for
every instance it finds. We send one request per concept and paint every
instance into a full-frame union mask, so "coverage" is the share of the
frame covered by at least one instance of that concept.

    from fieldnotes.segment import segment_concepts
    result = segment_concepts(Path("photos/north-ridge/2026-10-28_wide.jpg"),
                              ["weed", "bare soil", "daikon leaf"])
    result.coverage  # {"weed": 61.2, "bare soil": 18.5, "daikon leaf": 20.3}

Output of SAM is parsed with Meta's own `meta_sam_parser`; masks are decoded
to a row-major 0/1 raster covering only the instance's bounding box, which we
place into the frame at `bounds`.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from meta_sam_parser import (
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    decode_mask_to_raster,
    image_segmentation_format,
    parse_responses_stream,
)
from openai import AsyncOpenAI
from PIL import Image, ImageOps

from .llm import api_key

MODEL = "sam-3.1"
# Measured on a real field photo (2026-10-28): "flower cluster" found 6-7
# goldenrod heads at 1024 px and none at 1500 or 2048 px. Phone photos are
# ~4000 px, so SAM always gets a 1024 px copy.
SAM_SIDE = 1024
BASE_URL = "https://api.meta.ai/v1"


@dataclass
class Instance:
    object_id: int
    box: tuple[int, int, int, int]  # left, top, right, bottom (right/bottom exclusive)
    pixels: int
    confidence: float | None = None


@dataclass
class ConceptResult:
    concept: str
    width: int
    height: int
    instances: list[Instance] = field(default_factory=list)
    union: np.ndarray | None = None  # (height, width) uint8, 1 where any instance

    @property
    def coverage(self) -> float:
        if self.union is None:
            return 0.0
        return round(100.0 * float(self.union.sum()) / (self.width * self.height), 1)


@dataclass
class SegmentResult:
    photo: Path
    width: int
    height: int
    concepts: dict[str, ConceptResult]

    @property
    def coverage(self) -> dict[str, float]:
        return {c: r.coverage for c, r in self.concepts.items()}


# ---------------------------------------------------------------------------


def load_image_as_data_url(path: Path, max_side: int = 2048) -> tuple[str, int, int]:
    """Read, apply EXIF rotation, shrink to max_side, return (data URL, w, h).

    SAM reports coordinates in the pixels of the media *as sent*, so the size
    returned here is the frame size every mask refers to.
    """
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((max_side, max_side))
    from io import BytesIO

    buf = BytesIO()
    im.save(buf, format="JPEG", quality=90)
    data = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{data}", im.width, im.height


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(base_url=BASE_URL, api_key=api_key())


async def _segment_one(client: AsyncOpenAI, concept: str, image_url: str, width: int, height: int,
                       confidence: bool = True) -> ConceptResult:
    stream = await client.responses.create(
        model=MODEL,
        stream=True,
        input=[{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": concept},
                {"type": "input_image", "image_url": image_url},
            ],
        }],
        metadata={"include_confidence": "true"} if confidence else None,
    )
    parsed = parse_responses_stream(stream, image_segmentation_format())
    result = await parsed.final_result()
    return records_to_concept(concept, width, height, result.records)


def records_to_concept(concept: str, width: int, height: int, records) -> ConceptResult:
    """Pure function: parser records -> ConceptResult. Testable without the API."""
    out = ConceptResult(concept=concept, width=width, height=height)
    union = np.zeros((height, width), dtype=np.uint8)
    boxes: dict[int, SegmentationBoxRecord] = {}
    for r in records:
        if isinstance(r, SegmentationBoxRecord):
            boxes[r.object_id] = r
        elif isinstance(r, SegmentationMaskRecord):
            b = r.bounds
            raster = np.frombuffer(decode_mask_to_raster(r.mask), dtype=np.uint8)
            raster = raster.reshape(r.mask.height, r.mask.width)
            # Clip to the frame in case a mask runs off the edge.
            top, left = max(b.top, 0), max(b.left, 0)
            bottom, right = min(b.bottom, height), min(b.right, width)
            sub = raster[top - b.top : bottom - b.top, left - b.left : right - b.left]
            union[top:bottom, left:right] |= sub
            box = boxes.get(r.object_id)
            out.instances.append(Instance(
                object_id=r.object_id,
                box=(box.left, box.top, box.right, box.bottom) if box else (b.left, b.top, b.right, b.bottom),
                pixels=int(sub.sum()),
                confidence=r.confidence,
            ))
    out.union = union
    return out


async def segment_concepts_async(photo: Path, concepts: list[str], max_side: int = SAM_SIDE) -> SegmentResult:
    image_url, w, h = load_image_as_data_url(photo, max_side)
    client = _client()
    results = await asyncio.gather(*(_segment_one(client, c, image_url, w, h) for c in concepts))
    return SegmentResult(photo=photo, width=w, height=h, concepts={r.concept: r for r in results})


def segment_concepts(photo: Path, concepts: list[str], max_side: int = SAM_SIDE) -> SegmentResult:
    return asyncio.run(segment_concepts_async(photo, concepts, max_side))


def save_overlay(result: SegmentResult, out: Path, colours: dict[str, tuple[int, int, int]] | None = None) -> Path:
    """Write the photo with each concept's union mask tinted, for the record and the demo."""
    im = ImageOps.exif_transpose(Image.open(result.photo)).convert("RGB")
    im.thumbnail((result.width, result.height))
    base = np.asarray(im).astype(np.float32)
    palette = colours or {}
    default = [(220, 40, 40), (40, 160, 40), (40, 80, 220), (220, 160, 40), (160, 40, 200)]
    colour = {name: palette.get(name, default[i % len(default)]) for i, name in enumerate(result.concepts)}
    # largest first, so small objects (flower heads) stay visible on a mask that covers the whole field
    for name, c in sorted(result.concepts.items(), key=lambda kv: -kv[1].coverage):
        if c.union is None or not c.union.any():
            continue
        rgb = np.array(colour[name], dtype=np.float32)
        m = c.union.astype(bool)
        base[m] = base[m] * 0.5 + rgb * 0.5
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(base.astype(np.uint8)).save(out)
    return out
