"""Shared constants between CLI and skill — vision prompt, routing, doc template."""

from __future__ import annotations

CONTENT_TYPES = (
    "notes",
    "diagram",
    "drawing",
    "principles",
    "screenshot",
    "photo",
    "mixed",
)

DEFAULT_SUBFOLDERS: dict[str, str] = {
    "notes": "notes",
    "diagram": "diagrams",
    "drawing": "drawings",
    "principles": "principles",
    "screenshot": "screenshots",
    "photo": "photos",
    "mixed": "uploads",
}

DEFAULT_VAULT_ROOT = "Inbox/AirDrop"

ANALYSIS_TOOL = {
    "name": "record_analysis",
    "description": (
        "Record a structured analysis of the image. Always call this exactly "
        "once. The fields drive routing and document generation."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": (
                    "3 to 8 words derived from the document content (not the "
                    "filename). Title-case, no trailing punctuation."
                ),
            },
            "content_type": {
                "type": "string",
                "enum": list(CONTENT_TYPES),
                "description": (
                    "What kind of content is captured. Drives the destination "
                    "subfolder."
                ),
            },
            "ocr_text": {
                "type": "string",
                "description": (
                    "Full readable text. Preserve structure: keep headings as "
                    "Markdown headings, bullets as `-`, ordered lists as `1.`. "
                    "If the image has no text, return an empty string."
                ),
            },
            "summary": {
                "type": "string",
                "description": "1 to 3 sentences describing what the image contains.",
            },
            "key_concepts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topics, names, or terms worth indexing. May be empty.",
            },
            "visual_description": {
                "type": "string",
                "description": (
                    "If the image contains a diagram, drawing, or sketch, "
                    "describe its structure (nodes, arrows, labels, layout) so "
                    "the document is useful even without the image. Otherwise "
                    "return an empty string."
                ),
            },
        },
        "required": ["title", "content_type", "ocr_text", "summary"],
    },
}

SYSTEM_PROMPT = """You analyze images for an Obsidian-vault import tool.

The user AirDrops physical artifacts (handwritten notes, whiteboards, sketches,
diagrams, printed pages, screenshots) from their phone to their laptop. Your
job is to extract the content faithfully and classify it for routing.

Always respond by calling the `record_analysis` tool exactly once. Do not
include conversational text. If the image is empty or unreadable, still call
the tool with the best honest description you can give and `content_type`
set to `mixed`.

Quality rules:
- Derive titles from the *content*, never from filenames or metadata.
- Preserve structure in OCR: headings stay headings, bullets stay bullets.
- Diagrams: describe topology, labels, and direction so the doc reads well
  even if the image is lost.
- Be terse. Two short sentences beat a paragraph that says the same thing.
"""

DOC_TEMPLATE = """# {title}

> Captured {captured_at} via AirDrop{device_suffix}
> Source: `{source_filename}`

![[{image_link}]]

## Content

{ocr_text}

## Analysis

{summary}
{key_concepts_block}{visual_block}
---
*Imported by image2obsidian on {imported_at}*
"""


def render_doc(
    *,
    title: str,
    captured_at: str,
    device: str | None,
    source_filename: str,
    image_link: str,
    ocr_text: str,
    summary: str,
    key_concepts: list[str] | None,
    visual_description: str | None,
    imported_at: str,
) -> str:
    """Render a Markdown document for the Obsidian vault.

    image_link is the vault-relative path used in the `![[wikilink]]`.
    """
    device_suffix = f" from {device}" if device else ""
    ocr_body = ocr_text.strip() or "_No readable text._"

    if key_concepts:
        bullets = "\n".join(f"- {c}" for c in key_concepts)
        key_concepts_block = f"\n\n**Key concepts:**\n{bullets}"
    else:
        key_concepts_block = ""

    if visual_description and visual_description.strip():
        visual_block = f"\n\n**Visual:** {visual_description.strip()}"
    else:
        visual_block = ""

    return DOC_TEMPLATE.format(
        title=title,
        captured_at=captured_at,
        device_suffix=device_suffix,
        source_filename=source_filename,
        image_link=image_link,
        ocr_text=ocr_body,
        summary=summary.strip(),
        key_concepts_block=key_concepts_block,
        visual_block=visual_block,
        imported_at=imported_at,
    )
