"""Nonrecursive audiobook discovery and filename parsing."""
from __future__ import annotations

from pathlib import Path

from audiobook_fetcher.domain.models import Query

SUPPORTED_EXTENSIONS = frozenset({".mp3", ".m4b", ".m4a"})


def parse_filename(path: Path) -> Query:
    stem = path.stem.strip()
    if " - " in stem:
        author, title = stem.split(" - ", 1)
        return Query(title=title.strip(), author=author.strip() or None)
    return Query(title=stem, author=None)


def scan_directory(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise NotADirectoryError(directory)
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and not path.name.startswith(".")),
        key=lambda path: path.name.casefold(),
    )
