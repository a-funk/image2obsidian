# image2obsidian

> Bridge AirDropped iPhone photos into your Obsidian vault. OCR, classify, and route — automatically.

I like living in the real world. I like paper and pens. I like brushes and paint (shameless [artfunk](https://www.artfunk.org) plug). I do not want everything in my life to be entirely digital.  Todo lists, diagrams, charts, whatever - I love a notebook.  But I had relevant context I wanted to share with my agents in some of these notes. So I built image2obsidian - an open source spinoff of a small part of www.toto.tech.  

I have found it very useful and I hope you will too. 

Take a photo with an iPhone -> Airdrop it to the device running your agent -> i2o takes the image, semantically analyzes it and incorporates it into your obisidian vault right where it belongs. 

`image2obsidian` watches your Downloads folder for AirDropped images, runs OCR and content analysis with Claude's vision model, and writes structured Markdown documents into your Obsidian vault — sorted into subfolders by content type, with the original image attached as a wikilink.

Works two ways. Same routing rules, same document format, same vault layout:

- **CLI** — `pip install image2obsidian`. Scriptable, scheduleable, anyone with an Anthropic API key.
- **Claude Code skill** — drop the `SKILL.md` into your Claude Code skills directory. No API key needed; uses Claude Code's built-in vision.

Both paths are MIT-licensed. Both are open source.

## Why

Most people who keep a serious knowledge base in Obsidian have a "physical world to digital" gap. Things you write on paper, sketch on a whiteboard, or scrawl in a notebook never make it in — not because you don't want them to, but because the friction (transcribe, classify, file) is just high enough to lose every time.

This tool closes that gap with one keystroke. Take a photo, AirDrop it, run `image2obsidian`. The note is in the vault, OCR'd, classified, and linked to the original image, in seconds.

## Install

### CLI

```bash
pip install image2obsidian
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Create `~/.image2obsidian.json`:

```json
{
  "vault_path": "/absolute/path/to/your/Obsidian Vault",
  "vault_root": "Inbox/AirDrop"
}
```

That's it.

### Claude Code skill

If you use [Claude Code](https://claude.com/claude-code), you can use this without installing anything Python-side. Drop `SKILL.md` into your Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills/image2obsidian
curl -o ~/.claude/skills/image2obsidian/SKILL.md \
  https://raw.githubusercontent.com/a-funk/image2obsidian/main/SKILL.md
```

Then create `~/.image2obsidian.json` (same config as the CLI) and run `/image2obsidian` inside Claude Code.

## Usage

```bash
image2obsidian                  # scan AirDrops from the last 24 hours
image2obsidian --hours 48       # last 48 hours
image2obsidian --all            # every AirDrop in Downloads
image2obsidian --file IMG.jpg   # process one specific image
image2obsidian --dry-run        # show plan, write nothing
image2obsidian --yes            # skip the interactive picker
```

The Claude Code skill takes the same arguments via `/image2obsidian --hours 48`.

### Example

You AirDropped a hand-drawn architecture sketch and a page of meeting notes. You run `image2obsidian`:

```
=== AirDrop scan — 2 image(s) ===

  1. IMG_2401.jpg — May 6, 11:14 AM — iPhone 16 Pro
  2. IMG_2402.HEIC — May 6, 11:15 AM — iPhone 16 Pro

Process which? ("all", numbers like "1 3", or "none") [all]: all

=== Processing 2 image(s) with claude-sonnet-4-6 ===

  IMG_2401.jpg …
    ✓ Inbox/AirDrop/diagrams/sync-engine-architecture.md
  IMG_2402.HEIC …
    ✓ Inbox/AirDrop/notes/q2-planning-meeting-notes.md

=== Done — 2 written, 0 failed ===
```

Each Markdown doc has the OCR'd content, a summary, key concepts, and the
original image inline-rendered via wikilink. The image is copied into the
same subfolder so the link stays valid even if you move the vault.

## How AirDrop detection works

The single most reliable signal on macOS is the `com.apple.quarantine` extended attribute. AirDrop sets it with the `sharingd` agent name:

```
0081;{hex_timestamp};sharingd;{UUID}
```

The hex field decodes to the receive time. Local screenshots have no quarantine attribute. Browser downloads use the browser name (e.g. `Chrome`) instead of `sharingd`. So checking for `sharingd` in the quarantine string is a perfect AirDrop filter.

Full investigation in [`docs/airdrop-detection.md`](docs/airdrop-detection.md).

## Configuration

Full config, with all optional fields:

```json
{
  "vault_path": "/absolute/path/to/your/Obsidian Vault",
  "vault_root": "Inbox/AirDrop",
  "downloads_path": "~/Downloads",
  "default_hours": 24,
  "model": "claude-sonnet-4-6",
  "subfolders": {
    "notes": "notes",
    "diagram": "diagrams",
    "drawing": "drawings",
    "principles": "principles",
    "screenshot": "screenshots",
    "photo": "photos",
    "mixed": "uploads"
  }
}
```

You can override any of these with CLI flags (`--vault`, `--config`, `--model`) or env vars (`IMAGE2OBSIDIAN_VAULT`, `IMAGE2OBSIDIAN_CONFIG`).

## Document format

Every imported image becomes a Markdown doc shaped like this:

```markdown
# Sync Engine Architecture

> Captured 2026-05-06 11:14 via AirDrop from iPhone 16 Pro
> Source: `IMG_2401.jpg`

![[Inbox/AirDrop/diagrams/sync-engine-architecture.jpg]]

## Content

(OCR'd text, structure preserved)

## Analysis

Two-tier sync: local SQLite store mirrors a Postgres source of truth via
last-writer-wins per row. Conflict resolution defers to the server.

**Key concepts:**
- last-writer-wins
- SQLite mirror
- Postgres source of truth

**Visual:** Three boxes (Client, Local DB, Server) connected by labeled
arrows. Sync engine sits between Client and Local DB.

---
*Imported by image2obsidian on 2026-05-06 11:15*
```

The image is copied into the same subfolder as the doc and linked with a wikilink. Both the doc and the image use the same slug (lowercased, hyphenated title), so collisions are easy to spot and handle.

## Platform support

macOS only. AirDrop detection relies on `xattr` and `sips`, which are macOS-specific.

For Linux/Windows users, the CLI works fine on a folder of arbitrary images via `--file` — it just can't auto-filter to "AirDropped today". Pull requests for other platforms welcome.

## Development

```bash
git clone https://github.com/a-funk/image2obsidian
cd image2obsidian
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE). Use it for whatever you want, commercial or otherwise.

## Acknowledgements

Originally extracted from the [Toto](https://toto.tech) project's `/toto-digest` skill, which had the same job but tightly coupled to Toto's task system. This is the same idea, generalized for everyone who lives in Obsidian.
