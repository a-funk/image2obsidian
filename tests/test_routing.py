"""Routing logic tests — slug generation and collision avoidance."""

from __future__ import annotations

from pathlib import Path

import pytest

from image2obsidian.config import Config
from image2obsidian.routing import plan_destination, slugify


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Sync Engine Architecture", "sync-engine-architecture"),
        ("  Trailing & leading?? ", "trailing-leading"),
        ("Q2 Planning — 2026!", "q2-planning-2026"),
        ("", "untitled"),
        ("***", "untitled"),
    ],
)
def test_slugify(title, expected):
    assert slugify(title) == expected


def test_slugify_max_len():
    long = "a" * 200
    assert len(slugify(long)) <= 60


def test_plan_destination_basic(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    config = Config(vault_path=vault, vault_root="Inbox/AirDrop")
    source = tmp_path / "IMG_1849.JPG"
    source.write_bytes(b"fake")

    dest = plan_destination(
        config,
        title="Q2 Planning Notes",
        content_type="notes",
        source=source,
    )
    assert dest.doc_path == vault / "Inbox/AirDrop/notes/q2-planning-notes.md"
    assert dest.image_path == vault / "Inbox/AirDrop/notes/q2-planning-notes.jpg"
    assert dest.image_link == "Inbox/AirDrop/notes/q2-planning-notes.jpg"


def test_plan_destination_collision(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "Inbox/AirDrop/notes").mkdir(parents=True)
    (vault / "Inbox/AirDrop/notes/foo.md").write_text("existing")
    config = Config(vault_path=vault, vault_root="Inbox/AirDrop")
    source = tmp_path / "IMG.JPG"
    source.write_bytes(b"fake")

    dest = plan_destination(config, title="Foo", content_type="notes", source=source)
    assert dest.doc_path.name == "foo 2.md"


def test_plan_destination_unknown_type_falls_back(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    config = Config(vault_path=vault, vault_root="Inbox/AirDrop")
    source = tmp_path / "IMG.png"
    source.write_bytes(b"fake")

    dest = plan_destination(
        config,
        title="Mystery",
        content_type="something_unmapped",
        source=source,
    )
    assert "uploads" in dest.doc_path.parts
