"""Claude API vision client for image analysis.

Uses structured tool-use to force a JSON response, prompt caching for batch
runs (the system prompt is large and identical across every image), and
returns a typed `Analysis` dataclass.
"""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path

from anthropic import Anthropic

from .spec import ANALYSIS_TOOL, CONTENT_TYPES, SYSTEM_PROMPT

DEFAULT_MODEL = "claude-sonnet-4-6"
HEIC_MIME = "image/heic"


@dataclass(frozen=True)
class Analysis:
    title: str
    content_type: str
    ocr_text: str
    summary: str
    key_concepts: list[str]
    visual_description: str


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".heic", ".heif"):
        return HEIC_MIME
    mt, _ = mimetypes.guess_type(path.name)
    return mt or "image/jpeg"


def _load_image_b64(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    return _mime_type(path), base64.standard_b64encode(data).decode("ascii")


def _coerce_analysis(payload: dict) -> Analysis:
    content_type = payload.get("content_type", "mixed")
    if content_type not in CONTENT_TYPES:
        content_type = "mixed"
    return Analysis(
        title=str(payload.get("title", "")).strip() or "Untitled",
        content_type=content_type,
        ocr_text=str(payload.get("ocr_text", "")),
        summary=str(payload.get("summary", "")).strip(),
        key_concepts=[str(c) for c in payload.get("key_concepts", []) if str(c).strip()],
        visual_description=str(payload.get("visual_description", "")).strip(),
    )


class VisionClient:
    """Wraps the Anthropic SDK with the image2obsidian vision contract."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 2048,
    ) -> None:
        self._client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def analyze(self, image_path: Path) -> Analysis:
        mime, b64 = _load_image_b64(image_path)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "record_analysis"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this image (filename: {image_path.name}).",
                        },
                    ],
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "record_analysis":
                return _coerce_analysis(dict(block.input))

        raise RuntimeError(
            "Claude did not call record_analysis. Response: "
            + repr(response.content)
        )
