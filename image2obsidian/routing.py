"""Filename + folder selection for Obsidian writes."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import Config

SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class Destination:
    doc_path: Path
    image_path: Path
    image_link: str  # vault-relative, used inside ![[...]]


def slugify(text: str, max_len: int = 60) -> str:
    s = SLUG_RE.sub("-", text.lower()).strip("-")
    return (s or "untitled")[:max_len].rstrip("-")


def _unique(path: Path) -> Path:
    """Append ` 2`, ` 3` … before the suffix until path is unused."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    parent = path.parent
    n = 2
    while True:
        candidate = parent / f"{stem} {n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def plan_destination(
    config: Config,
    *,
    title: str,
    content_type: str,
    source: Path,
) -> Destination:
    subfolder = config.subfolders.get(content_type, config.subfolders.get("mixed", "uploads"))
    folder = config.root_dir / subfolder
    slug = slugify(title)
    doc = _unique(folder / f"{slug}.md")
    image = _unique(folder / f"{slug}{source.suffix.lower()}")

    vault_rel = image.relative_to(config.vault_path).as_posix()
    return Destination(doc_path=doc, image_path=image, image_link=vault_rel)


def write_destination(dest: Destination, *, doc_body: str, source_image: Path) -> None:
    dest.doc_path.parent.mkdir(parents=True, exist_ok=True)
    dest.doc_path.write_text(doc_body)
    shutil.copy2(source_image, dest.image_path)
