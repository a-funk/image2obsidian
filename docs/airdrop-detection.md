# AirDrop Detection on macOS

The single most reliable way to identify an AirDropped file on macOS is the
`com.apple.quarantine` extended attribute. This document records the
investigation that led to that conclusion, so future contributors can verify
the choice or update it if Apple changes the format.

## The signal

Inspect any AirDropped file with:

```bash
xattr -p com.apple.quarantine ~/Downloads/IMG_1849.jpg
```

You'll see something like:

```
0081;65d8a0e2;sharingd;A4F2B8E3-1234-5678-9ABC-DEF012345678
```

The fields are semicolon-separated:

| Field | Example | Meaning |
|-------|---------|---------|
| Flags | `0081` | Quarantine flags (origin + state) |
| Timestamp | `65d8a0e2` | Hex Unix epoch (seconds) — receive time |
| Agent | `sharingd` | The macOS daemon that wrote the xattr |
| UUID | `A4F2B8E3-…` | Per-file event UUID |

`sharingd` is the macOS Sharing daemon — it handles AirDrop, Handoff, and
related sharing flows. **No other source produces a quarantine xattr with
`sharingd` as the agent.** That makes the third field a perfect AirDrop
filter.

## Why not other signals?

| Signal | Why it's insufficient |
|--------|----------------------|
| EXIF `Make: Apple` / `Model: iPhone *` | Caught by photos taken on an iPhone, even if synced via Photos.app or copied via cable. False positives. |
| Filename pattern `IMG_\d{4}` | iPhone naming convention, but also matches files renamed manually or copied from any Apple device. False positives. |
| Display P3 color profile | Many Apple-shot photos. Same issue. |
| File mtime | Reflects copy time, not transfer source. False positives from any recent file. |
| `~/Library/SharingdProfile.plist` | Per-device pairing, doesn't tell you what was just received. |

The quarantine `sharingd` check beats all of these on its own.

## Browser downloads (false-positive trap)

Browser downloads also set `com.apple.quarantine`, but with a different agent
name:

```
0083;65d99988;com.google.Chrome;UUID...
0083;65d99988;com.apple.Safari;UUID...
```

So checking for the literal string `sharingd` in the agent field rules them
out cleanly.

## Local screenshots

Files that originate on the same Mac (screenshots, drag-saves, app exports)
have **no quarantine attribute at all**. `xattr -p com.apple.quarantine`
returns a non-zero exit code. Treat that as "not AirDropped."

## The `IMG_XXXX 2.jpg` duplicate

When the user AirDrops the same file twice, macOS doesn't overwrite — it
saves the second copy as `IMG_1849 2.jpg`, then `IMG_1849 3.jpg`, etc. Both
copies have valid `sharingd` quarantine attributes, so the detection logic
sees them both. Skip the numbered duplicates by default; the original is
already there.

Regex: `^(IMG_\d{4}) \d+(\.[a-z]+)$` (case-insensitive).

## Decoding the timestamp

```python
import datetime
hex_ts = quarantine_value.split(";")[1]
received_at = datetime.datetime.fromtimestamp(int(hex_ts, 16))
```

This is the receive time, not the photo capture time. To get capture time
you'd parse EXIF — but for "what did I AirDrop today?" the receive time is
exactly what you want.

## Edge cases

- **HEIC/HEIF:** AirDrops of Live Photos and high-efficiency images get
  `.heic` extensions. They have the same quarantine signal. Supported.
- **Album AirDrop:** AirDropping a photo album sends each photo as its own
  file with its own quarantine xattr. Supported (each is processed
  independently).
- **iCloud Shared Albums:** these are not AirDrop and have no `sharingd`
  signal. Out of scope.

## Future-proofing

If Apple ever renames `sharingd` or changes the quarantine format, this
detection breaks silently — files would simply stop being recognized as
AirDrops. The mitigation is the corroborating-signals fallback documented in
the skill (`IMG_\d{4}` filename pattern + recent mtime), with a warning that
detection confidence is reduced. As of macOS 14 (Sonoma) and 15 (Sequoia),
the format is stable.
