"""Read embedded audiobook metadata with mutagen."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from mutagen import File

from audiobook_fetcher.domain.models import AudiobookCandidate


def _first(tags, *keys: str) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value:
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            if value is not None and str(value).strip():
                return str(value).strip()
    return None


def _number(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.split("/", 1)[0])
    except ValueError:
        return None


def _year(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date(int(value[:4]), 1, 1)
    except (ValueError, TypeError):
        return None


def read_metadata(path: Path) -> tuple[AudiobookCandidate, str | None, int | None, int | None]:
    """Return book metadata, chapter title, track number, and disc number.

    Album is treated as audiobook title; per-file title becomes chapter title
    when it differs from album. This keeps multi-file books grouped together.
    """
    audio = File(path, easy=True)
    if audio is None:
        raise ValueError(f"unsupported or unreadable audio file: {path}")
    tags = audio.tags or {}
    file_title = _first(tags, "title") or path.stem
    book_title = _first(tags, "album") or file_title
    artists = [x for x in (tags.get("artist") or tags.get("albumartist") or []) if str(x).strip()]
    if isinstance(artists, str):
        artists = [artists]
    genres = tags.get("genre") or []
    if isinstance(genres, str):
        genres = [genres]
    candidate = AudiobookCandidate(
        source_name="embedded",
        source_id=str(path),
        title=book_title,
        authors=[str(x) for x in artists],
        narrators=[str(x) for x in (tags.get("composer") or [])] if not isinstance(tags.get("composer"), str) else [str(tags["composer"])],
        published_date=_year(_first(tags, "date", "year")),
        genres=[str(x) for x in genres],
        description=_first(tags, "description", "comment"),
        duration_seconds=round(audio.info.length) if getattr(audio, "info", None) and audio.info.length else None,
    )
    chapter = file_title if file_title.casefold() != book_title.casefold() else None
    return candidate, chapter, _number(_first(tags, "tracknumber")), _number(_first(tags, "discnumber"))
