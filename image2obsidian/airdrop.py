"""AirDrop detection for macOS Downloads folder.

The single most reliable AirDrop signal on macOS is the `com.apple.quarantine`
extended attribute containing the `sharingd` agent. Quarantine format:

    0081;{hex_timestamp};sharingd;{UUID}

The hex timestamp is seconds since the Unix epoch — it's the receive time.

Local screenshots have no quarantine attribute. Browser downloads have
quarantine but with the browser name (`Chrome`, `Safari`, etc.) instead of
`sharingd`.

See docs/airdrop-detection.md for the full investigation.
"""

from __future__ import annotations

import datetime as dt
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

QUARANTINE_ATTR = "com.apple.quarantine"
SHARINGD_AGENT = "sharingd"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
IPHONE_FILENAME_RE = re.compile(r"^IMG_\d{4}( \d+)?\.(jpe?g|png|heic|heif)$", re.IGNORECASE)
DUPLICATE_SUFFIX_RE = re.compile(r"^(IMG_\d{4}) \d+(\.[a-z]+)$", re.IGNORECASE)


@dataclass(frozen=True)
class AirDropImage:
    path: Path
    received_at: dt.datetime
    device: str | None
    quarantine_uuid: str | None

    @property
    def is_duplicate_marker(self) -> bool:
        """macOS appends ` 2`, ` 3` etc. when the same file arrives twice."""
        return bool(DUPLICATE_SUFFIX_RE.match(self.path.name))


def parse_quarantine(value: str) -> tuple[dt.datetime, str, str] | None:
    """Parse a quarantine xattr value.

    Returns (received_at, agent, uuid) or None if the value isn't a sharingd
    quarantine string.
    """
    parts = value.strip().split(";")
    if len(parts) < 4:
        return None
    _flags, hex_ts, agent, uuid = parts[:4]
    if agent != SHARINGD_AGENT:
        return None
    try:
        ts = int(hex_ts, 16)
    except ValueError:
        return None
    return dt.datetime.fromtimestamp(ts), agent, uuid


def read_quarantine(path: Path) -> str | None:
    """Read the raw quarantine xattr, or None if absent."""
    try:
        out = subprocess.run(
            ["xattr", "-p", QUARANTINE_ATTR, str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def read_device(path: Path) -> str | None:
    """Read iPhone model via `sips`, e.g. 'iPhone 16 Pro'. None on failure."""
    try:
        out = subprocess.run(
            ["sips", "-g", "make", "-g", "model", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if out.returncode != 0:
        return None
    make = model = None
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("make:"):
            make = line.split(":", 1)[1].strip()
        elif line.startswith("model:"):
            model = line.split(":", 1)[1].strip()
    if make and model:
        return f"{make} {model}".strip()
    return model or None


def scan_airdrops(
    downloads: Path,
    *,
    since: dt.datetime | None = None,
    include_duplicates: bool = False,
) -> list[AirDropImage]:
    """Scan a Downloads-shaped directory for AirDropped images.

    Args:
        downloads: Directory to scan. Not recursive.
        since: Only return images received at or after this time. None = all.
        include_duplicates: If False (default), skip macOS `IMG_XXXX 2.jpg`
            duplicates created when the same file is AirDropped twice.

    Returns images sorted newest-first.
    """
    if not downloads.is_dir():
        return []

    results: list[AirDropImage] = []
    for entry in downloads.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() not in IMAGE_EXTS:
            continue
        raw = read_quarantine(entry)
        if raw is None:
            continue
        parsed = parse_quarantine(raw)
        if parsed is None:
            continue
        received_at, _agent, uuid = parsed
        if since is not None and received_at < since:
            continue
        device = read_device(entry)
        img = AirDropImage(
            path=entry,
            received_at=received_at,
            device=device,
            quarantine_uuid=uuid,
        )
        if not include_duplicates and img.is_duplicate_marker:
            continue
        results.append(img)

    results.sort(key=lambda i: i.received_at, reverse=True)
    return results


def filter_already_imported(
    images: list[AirDropImage],
    imported_filenames: set[str],
) -> list[AirDropImage]:
    """Drop images whose source filename has already been imported."""
    return [img for img in images if img.path.name not in imported_filenames]
