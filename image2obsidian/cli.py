"""image2obsidian CLI — scan AirDrops, run vision, write to Obsidian."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .airdrop import AirDropImage, scan_airdrops
from .config import Config, ConfigError, load_config
from .routing import plan_destination, write_destination
from .spec import render_doc
from .vision import DEFAULT_MODEL, VisionClient

app = typer.Typer(
    add_completion=False,
    help="Bridge AirDropped images into your Obsidian vault.",
)


def _err(msg: str) -> None:
    typer.echo(f"error: {msg}", err=True)


def _resolve_since(hours: int | None, all_flag: bool) -> dt.datetime | None:
    if all_flag:
        return None
    return dt.datetime.now() - dt.timedelta(hours=hours or 24)


def _format_candidates(images: list[AirDropImage]) -> str:
    lines = []
    for i, img in enumerate(images, 1):
        when = img.received_at.strftime("%b %d, %I:%M %p")
        device = img.device or "unknown device"
        lines.append(f"  {i}. {img.path.name} — {when} — {device}")
    return "\n".join(lines)


def _pick(images: list[AirDropImage], answer: str) -> list[AirDropImage]:
    answer = answer.strip().lower()
    if answer in ("none", "n", "no", ""):
        return []
    if answer in ("all", "a", "yes", "y"):
        return list(images)
    picked: list[AirDropImage] = []
    for token in answer.replace(",", " ").split():
        try:
            idx = int(token)
        except ValueError:
            continue
        if 1 <= idx <= len(images):
            picked.append(images[idx - 1])
    return picked


def _process_one(
    img: AirDropImage,
    *,
    config: Config,
    client: VisionClient,
    dry_run: bool,
) -> tuple[AirDropImage, Path | None]:
    analysis = client.analyze(img.path)
    dest = plan_destination(
        config,
        title=analysis.title,
        content_type=analysis.content_type,
        source=img.path,
    )
    captured_at = img.received_at.strftime("%Y-%m-%d %H:%M")
    imported_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = render_doc(
        title=analysis.title,
        captured_at=captured_at,
        device=img.device,
        source_filename=img.path.name,
        image_link=dest.image_link,
        ocr_text=analysis.ocr_text,
        summary=analysis.summary,
        key_concepts=analysis.key_concepts,
        visual_description=analysis.visual_description,
        imported_at=imported_at,
    )
    if dry_run:
        typer.echo(f"  [dry-run] would write {dest.doc_path}")
        return img, None
    write_destination(dest, doc_body=body, source_image=img.path)
    return img, dest.doc_path


@app.command()
def main(
    hours: int = typer.Option(None, "--hours", "-h", help="Look back N hours."),
    all_: bool = typer.Option(False, "--all", help="No time filter."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Process one specific image."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan without writing."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    vault: Optional[Path] = typer.Option(None, "--vault", help="Override vault path."),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Override config file."),
    model: Optional[str] = typer.Option(None, "--model", help="Override Claude model."),
    version: bool = typer.Option(False, "--version", help="Print version and exit."),
) -> None:
    """Scan AirDrops in your Downloads folder and import them into Obsidian."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()

    try:
        config = load_config(config_path, vault_override=vault)
    except ConfigError as e:
        _err(str(e))
        raise typer.Exit(code=2)

    chosen_model = model or config.model or DEFAULT_MODEL

    if file is not None:
        if not file.exists():
            _err(f"file not found: {file}")
            raise typer.Exit(code=2)
        images = [
            AirDropImage(
                path=file.resolve(),
                received_at=dt.datetime.fromtimestamp(file.stat().st_mtime),
                device=None,
                quarantine_uuid=None,
            )
        ]
    else:
        since = _resolve_since(hours, all_)
        images = scan_airdrops(config.downloads_path, since=since)
        if not images:
            window = "all time" if since is None else f"the last {hours or 24}h"
            typer.echo(f"No AirDropped images found in {window}.")
            raise typer.Exit()

        typer.echo(f"=== AirDrop scan — {len(images)} image(s) ===\n")
        typer.echo(_format_candidates(images))
        if not yes:
            answer = typer.prompt(
                '\nProcess which? ("all", numbers like "1 3", or "none")',
                default="all",
                show_default=True,
            )
            images = _pick(images, answer)
        if not images:
            typer.echo("Nothing to do.")
            raise typer.Exit()

    try:
        client = VisionClient(model=chosen_model)
    except Exception as e:
        _err(f"could not init Anthropic client: {e}")
        raise typer.Exit(code=2)

    typer.echo(f"\n=== Processing {len(images)} image(s) with {chosen_model} ===\n")
    written: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for img in images:
        typer.echo(f"  {img.path.name} …")
        try:
            _, doc = _process_one(img, config=config, client=client, dry_run=dry_run)
        except Exception as e:
            failed.append((img.path, str(e)))
            typer.echo(f"    ✗ {e}")
            continue
        if doc is not None:
            written.append(doc)
            typer.echo(f"    ✓ {doc.relative_to(config.vault_path)}")

    typer.echo(
        f"\n=== Done — {len(written)} written, {len(failed)} failed"
        + (" (dry-run)" if dry_run else "")
        + " ==="
    )
    if failed:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
