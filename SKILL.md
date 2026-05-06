---
name: image2obsidian
description: Scan ~/Downloads for AirDropped iPhone images, perform OCR/vision analysis, and route content into your Obsidian vault. Bridges physical artifacts to your world model.
user-invocable: true
---

# image2obsidian

Scan the user's Downloads folder for recently AirDropped iPhone images, run
OCR and content analysis using Claude's native vision, and write structured
Markdown documents into the Obsidian vault.

This skill is the Claude Code path for the `image2obsidian` project. The
companion CLI (`pip install image2obsidian`) does the same thing without
Claude Code, hitting the Anthropic API directly. Both paths share the same
routing rules and document format.

**Usage:**
- `/image2obsidian` — scan AirDrops from the last 24 hours
- `/image2obsidian --hours 48` — last 48 hours
- `/image2obsidian --all` — every AirDrop in Downloads
- `/image2obsidian --file PATH` — process one specific image
- `/image2obsidian --dry-run` — show plan, write nothing

## Configuration

Read `~/.image2obsidian.json`. Required:

```json
{
  "vault_path": "/absolute/path/to/Obsidian Vault",
  "vault_root": "Inbox/AirDrop"
}
```

Optional fields: `downloads_path`, `default_hours`, `subfolders` (override
per-content-type folder names).

If the config doesn't exist, ask the user to create it before proceeding.
Never guess vault paths.

## Steps

### 1. Load config

Read `~/.image2obsidian.json`. Verify `vault_path` exists. If missing:

```
Config not found at ~/.image2obsidian.json.

Create it with at minimum:
  { "vault_path": "/path/to/your/Obsidian Vault" }

Then run /image2obsidian again.
```

### 2. Parse arguments

From `$ARGUMENTS`:
- `--hours N` — look back N hours (default: 24, or `default_hours` from config)
- `--all` — no time filter
- `--file PATH` — skip scanning, process this specific file
- `--dry-run` — show what would be processed, write nothing

### 3. Scan Downloads for AirDropped images

Skip this step if `--file` was given.

**AirDrop detection** (validated on macOS):

```bash
# Step 1: list candidate image files (jpg, jpeg, png, heic, heif)
ls -t ~/Downloads/*.{jpg,jpeg,png,heic,JPG,JPEG,PNG,HEIC,heif,HEIF} 2>/dev/null
```

```bash
# Step 2: read the quarantine attribute. The DEFINITIVE signal is "sharingd".
xattr -p com.apple.quarantine <file> 2>/dev/null
```

**Detection rules:**
1. **Primary (definitive):** `com.apple.quarantine` contains `sharingd` — this IS an AirDrop file.
2. **Format:** `0081;{hex_timestamp};sharingd;{UUID}`. The hex field is seconds since the Unix epoch — that's the AirDrop receive time.
3. **Corroborating:** EXIF via `sips -g make -g model` (`Apple` / `iPhone *`), filename pattern `IMG_\d{4}\.(jpg|JPG|PNG|HEIC)`.

**Non-AirDrop exclusions:**
- Local screenshots have NO quarantine attribute.
- Browser downloads have quarantine, but with the browser name (`Chrome`, `Safari`) instead of `sharingd`.

**Time filter:** decode the hex timestamp to a `datetime`, then keep only files received within the `--hours` window.

**Skip duplicates:** macOS appends ` 2`, ` 3` to the filename when the same file is AirDropped twice (e.g. `IMG_1849 2.jpg`). Skip these.

### 4. Present candidates

Show what was found before processing:

```
=== AirDrop scan — 3 image(s) ===

  1. IMG_1849.jpg — Apr 12, 9:55 PM — iPhone 16 Pro
  2. IMG_1849 2.jpg — Apr 12, 9:55 PM — (duplicate, skipping)
  3. IMG_1837.JPG — Apr 10, 4:49 PM — iPhone 16 Pro

Process which? ("all", numbers like "1 3", or "none")
```

### 5. Read and analyze each image

For each confirmed image, use the `Read` tool to view the image. Claude's
multimodal vision performs OCR and content analysis natively — no external
library needed.

Extract:

| Field | Notes |
|-------|-------|
| **title** | 3 to 8 words derived from *content*, never from `IMG_XXXX` filenames |
| **content_type** | one of: `notes`, `diagram`, `drawing`, `principles`, `screenshot`, `photo`, `mixed` |
| **ocr_text** | full readable text, structure preserved (Markdown headings, bullets) |
| **summary** | 1 to 3 sentences describing the contents |
| **key_concepts** | array of topics, names, terms worth indexing |
| **visual_description** | for diagrams/drawings: describe topology, labels, layout — so the doc reads even without the image |

### 6. Route into the vault

Destination = `{vault_path}/{vault_root}/{subfolder}/{slug}.md`.

Default subfolder map (override via config `subfolders`):

| content_type | subfolder |
|--------------|-----------|
| notes        | `notes` |
| diagram      | `diagrams` |
| drawing      | `drawings` |
| principles   | `principles` |
| screenshot   | `screenshots` |
| photo        | `photos` |
| mixed        | `uploads` |

**Slug:** lowercase the title, replace runs of non-alphanumerics with `-`, trim, max 60 chars.

**Collisions:** if `{slug}.md` already exists, append ` 2`, ` 3`, etc. before the suffix. Same for the image copy.

**Document format** (mirrors the CLI exactly):

```markdown
# {Title}

> Captured {YYYY-MM-DD HH:MM} via AirDrop from {device}
> Source: `{original filename}`

![[{vault-relative path to copied image}]]

## Content

{OCR text — preserve structure, or `_No readable text._` if empty}

## Analysis

{summary}

**Key concepts:**
- {concept 1}
- {concept 2}

**Visual:** {visual_description, if non-empty}

---
*Imported by image2obsidian on {YYYY-MM-DD HH:MM}*
```

Omit the **Key concepts** block if the array is empty. Omit the **Visual**
line if `visual_description` is empty.

### 7. Copy the image into the vault

Copy the original image into the same subfolder as the doc, with the same
slug + the original extension (lowercased):

```bash
cp ~/Downloads/IMG_1849.jpg "{vault_path}/{vault_root}/{subfolder}/{slug}.jpg"
```

Use the vault-relative path of the copied image inside the `![[...]]` wikilink
in the doc body. Obsidian will inline-render the image.

### 8. Report results

```
=== Done — 2 written, 0 failed ===

  IMG_1849.jpg → Inbox/AirDrop/notes/digest-feature-notes.md (notes)
  IMG_1837.JPG → Inbox/AirDrop/principles/data-principles.md (principles)
```

If `--dry-run`, show the same plan but don't write anything.

## Content type cheat sheet

| Type | When to choose it |
|------|-------------------|
| `notes` | Handwritten or printed notes, prose, lists |
| `diagram` | Flowcharts, architecture sketches, graphs with labels |
| `drawing` | Sketches, doodles, art (less structured than `diagram`) |
| `principles` | Values, rules, axioms — short bullet-style content |
| `screenshot` | Phone or computer screenshots (UI text matters) |
| `photo` | Real-world photo, no document content |
| `mixed` | Multiple content types, or unclassifiable |

## Error handling

- **No AirDrops found:** "No AirDropped images found in the last {N} hours."
- **`xattr` unavailable:** fall back to filename pattern + recency, but warn that detection is less reliable.
- **Vault path missing:** stop and ask the user to fix `~/.image2obsidian.json`.
- **Image already imported:** if a doc with the same slug already exists in the target subfolder, ask the user before re-processing.

## Notes

- This skill ships with the open-source `image2obsidian` project. The CLI
  (`pip install image2obsidian`) does the same job without Claude Code, for
  users who prefer a standalone tool or want to script it.
- The quarantine `sharingd` check is the single most reliable AirDrop
  detection method on macOS. See `docs/airdrop-detection.md` in the repo for
  the full investigation.
- Document titles must come from the image content, never from filenames.
