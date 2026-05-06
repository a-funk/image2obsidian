"""Pure-logic tests for airdrop detection (no filesystem, no xattr)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from image2obsidian.airdrop import (
    AirDropImage,
    DUPLICATE_SUFFIX_RE,
    parse_quarantine,
)


def test_parse_quarantine_sharingd():
    raw = "0081;65d8a0e2;sharingd;A4F2B8E3-1234-5678-9ABC-DEF012345678"
    result = parse_quarantine(raw)
    assert result is not None
    received_at, agent, uuid = result
    assert agent == "sharingd"
    assert uuid.startswith("A4F2B8E3")
    assert received_at == dt.datetime.fromtimestamp(0x65d8a0e2)


def test_parse_quarantine_browser_rejected():
    raw = "0083;65d99988;com.google.Chrome;A4F2B8E3-1234-5678-9ABC-DEF012345678"
    assert parse_quarantine(raw) is None


def test_parse_quarantine_malformed():
    assert parse_quarantine("garbage") is None
    assert parse_quarantine("0081;notahex;sharingd;UUID") is None
    assert parse_quarantine("") is None


@pytest.mark.parametrize(
    "filename,is_dup",
    [
        ("IMG_1849.jpg", False),
        ("IMG_1849 2.jpg", True),
        ("IMG_1849 3.JPG", True),
        ("IMG_1849 12.heic", True),
        ("photo.jpg", False),
    ],
)
def test_duplicate_marker_regex(filename, is_dup):
    img = AirDropImage(
        path=Path(filename),
        received_at=dt.datetime.now(),
        device=None,
        quarantine_uuid=None,
    )
    assert img.is_duplicate_marker is is_dup
    assert bool(DUPLICATE_SUFFIX_RE.match(filename)) is is_dup
