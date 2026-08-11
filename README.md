# Audiobook Organizer

Organize audiobook files from embedded metadata or Open Library. The tool previews every move, requires approval, writes a durable manifest, and supports undo.

Linux MVP. Supported files: `.mp3`, `.m4b`, `.m4a`.

## Install

```bash
uv sync --extra dev
```

Run commands through the project environment:

```bash
uv run audiobook-fetcher --help
```

## Tag-based organization

Use this for audiobooks whose embedded metadata is already correct. It reads title, album, author, year, genre, description, duration, chapter title, and track number with `mutagen`.

```bash
uv run audiobook-fetcher plan /path/to/audiobooks \
  --source tags \
  --output-root /path/to/organized \
  --plan-file /path/to/approved-plan.json
```

`plan` scans one directory level, builds a preview, and opens the approval TUI. The plan is saved only after pressing `y` in the TUI. Press `q` to cancel without saving.

Default destination layout:

```text
{author}/{title} ({year})/{chapter_or_original}
```

Example multi-file book:

```text
Weir, Andy/Project Hail Mary (2021)/01 - Chapter One.mp3
Weir, Andy/Project Hail Mary (2021)/02 - Chapter Two.mp3
```

When chapter metadata is missing, the original filename is preserved so files remain recognizable.

## Open Library organization

Use network metadata when embedded tags are missing or unreliable:

```bash
uv run audiobook-fetcher plan /path/to/audiobooks \
  --source openlibrary \
  --output-root /path/to/organized \
  --plan-file /path/to/approved-plan.json
```

Open Library requests use a 10-second timeout. Individual lookup failures become skipped rows instead of aborting the entire preview.

## Commit and undo

`commit` moves originals; it does not copy them. Before moving, it blocks the whole batch if a source is missing, a destination exists, or destinations collide.

```bash
uv run audiobook-fetcher commit \
  /path/to/approved-plan.json \
  --manifest /path/to/.audiobook-fetcher/manifests/batch.json
```

Tags are written after a successful move. Tag failures are reported and the manifest remains usable for undo.

Undo a committed batch:

```bash
uv run audiobook-fetcher undo \
  /path/to/.audiobook-fetcher/manifests/batch.json
```

Undo is durable and safe to repeat. Move failures trigger best-effort reverse rollback while preserving the manifest.

## Google Drive with rclone

The application reads normal local paths. Mount a Drive remote read-only first:

```bash
mkdir -p /tmp/gdrive-audiobook-test
rclone mount gdrive-audiobook: /tmp/gdrive-audiobook-test \
  --read-only \
  --vfs-cache-mode full
```

Then preview one audiobook directory with a local output root:

```bash
uv run audiobook-fetcher plan \
  "/tmp/gdrive-audiobook-test/Some Audiobook" \
  --source tags \
  --output-root /tmp/audiobooks-organized \
  --plan-file /tmp/approved-plan.json
```

Do not point `--output-root` at a read-only mount. Unmount after testing:

```bash
fusermount -u /tmp/gdrive-audiobook-test
```

## Configuration

Optional TOML config. CLI values override config values, which override defaults:

```toml
input_dir = "/books/inbox"
output_root = "/books/organized"
pattern = "{author}/{title} ({year})/{chapter_or_original}"
timeout = 10
```

Use it with:

```bash
uv run audiobook-fetcher --config audiobook-fetcher.toml plan \
  --source tags \
  --plan-file /path/to/approved-plan.json
```

## Development

```bash
uv run pytest -q
uv run python -m compileall audiobook_fetcher
```

The test suite covers scanning, filename parsing, config precedence, embedded metadata extraction, chapter grouping, planning safety, commit/rollback, undo, and plan persistence.
