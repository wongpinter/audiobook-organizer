"""Turns AudiobookCandidate metadata into a proposed new path, and detects
collisions across a batch before anything is committed.
"""
from __future__ import annotations

import re
from pathlib import Path

from audiobook_fetcher.domain.models import AudiobookCandidate, RenamePlan

DEFAULT_PATTERN = "{author}/{title} ({year})/{chapter_or_original}"

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')


def _sanitize(component: str) -> str:
    return _INVALID_CHARS.sub("", component).strip()


def render_path(
    pattern: str,
    meta: AudiobookCandidate,
    original_file: Path,
    *,
    chapter_title: str | None = None,
    track_number: int | None = None,
    disc_number: int | None = None,
) -> Path:
    series_prefix = ""
    if meta.series:
        series_name = _sanitize(meta.series)
        index = f" {meta.series_index:g}" if meta.series_index is not None else ""
        series_prefix = f"{series_name}{index} - "

    tokens = {
        "author": _sanitize(meta.author_display()),
        "title": _sanitize(meta.title),
        "series": _sanitize(meta.series or ""),
        "series_prefix": series_prefix,
        "year": str(meta.published_date.year) if meta.published_date else "Unknown",
        "original_name": original_file.name,
        "chapter_title": _sanitize(chapter_title or ""),
        "chapter_or_original": (
            f"{track_number:02d} - {_sanitize(chapter_title)}{original_file.suffix}"
            if chapter_title and track_number is not None
            else f"{_sanitize(chapter_title)}{original_file.suffix}"
            if chapter_title
            else original_file.name
        ),
        "track_number": f"{track_number:02d}" if track_number is not None else "",
        "disc_number": f"{disc_number:02d}" if disc_number is not None else "",
    }
    rendered = pattern.format(**tokens)
    return Path(rendered)


def build_plan(
    files_with_matches: list[tuple[Path, AudiobookCandidate | None] | tuple[Path, AudiobookCandidate | None, str | None, int | None, int | None]],
    pattern: str = DEFAULT_PATTERN,
    output_root: Path | None = None,
) -> list[RenamePlan]:
    """Build a batch of RenamePlans, flagging conflicts before the user sees them."""
    plans: list[RenamePlan] = []

    for row in files_with_matches:
        old_path, metadata = row[:2]
        chapter_title = row[2] if len(row) > 2 else None
        track_number = row[3] if len(row) > 3 else None
        disc_number = row[4] if len(row) > 4 else None
        if metadata is None:
            plans.append(
                RenamePlan(
                    old_path=old_path,
                    new_path=None,
                    metadata=None,
                    include=False,
                    reason_skipped="no confident match",
                )
            )
            continue

        new_relative = render_path(
            pattern, metadata, old_path,
            chapter_title=chapter_title,
            track_number=track_number,
            disc_number=disc_number,
        )
        new_path = (output_root / new_relative) if output_root else new_relative
        new_path = new_path.resolve() if output_root else new_path
        old_resolved = old_path.resolve()
        if new_path == old_resolved:
            plans.append(RenamePlan(old_path=old_path, new_path=new_path, metadata=metadata, include=False, reason_skipped="already at destination", chapter_title=chapter_title, track_number=track_number, disc_number=disc_number))
        else:
            plans.append(RenamePlan(old_path=old_path, new_path=new_path, metadata=metadata, chapter_title=chapter_title, track_number=track_number, disc_number=disc_number))

    _flag_conflicts(plans)
    return plans


def _flag_conflicts(plans: list[RenamePlan]) -> None:
    seen: dict[Path, RenamePlan] = {}
    for plan in plans:
        if plan.new_path is None:
            continue
        if plan.new_path in seen:
            plan.include = False
            plan.reason_skipped = f"conflicts with {seen[plan.new_path].old_path.name}"
            seen[plan.new_path].include = False
            seen[plan.new_path].reason_skipped = f"conflicts with {plan.old_path.name}"
        else:
            seen[plan.new_path] = plan
