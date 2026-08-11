"""Writes AudiobookCandidate metadata into audio file tags via mutagen.

mutagen gives us one library across formats, but the tag *keys* differ per
container (ID3 frames for mp3 vs MP4 atoms for m4b/m4a), so we still need a
small per-format branch. This is the only place that branch lives.
"""
from __future__ import annotations

from pathlib import Path

from mutagen.id3 import ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from audiobook_fetcher.domain.models import AudiobookCandidate


class UnsupportedFormatError(Exception):
    pass


def write_tags(file_path: Path, metadata: AudiobookCandidate) -> None:
    suffix = file_path.suffix.lower()

    if suffix == ".mp3":
        _write_mp3(file_path, metadata)
    elif suffix in (".m4b", ".m4a"):
        _write_mp4(file_path, metadata)
    else:
        raise UnsupportedFormatError(f"no tag writer for {suffix} files")


def _write_mp3(file_path: Path, meta: AudiobookCandidate) -> None:
    audio = MP3(file_path)
    if audio.tags is None:
        audio.add_tags()
    tags: ID3 = audio.tags

    tags.setall("TIT2", [TIT2(encoding=3, text=meta.title)])
    if meta.authors:
        tags.setall("TPE1", [TPE1(encoding=3, text=meta.authors)])
    if meta.narrators:
        # No dedicated ID3 narrator frame; TPE2 (album artist) is the
        # conventional place audiobook apps look for it.
        tags.setall("TPE2", [TPE2(encoding=3, text=meta.narrators)])
    if meta.series:
        tags.setall("TALB", [TALB(encoding=3, text=meta.series)])
    if meta.published_date:
        tags.setall("TDRC", [TDRC(encoding=3, text=str(meta.published_date.year))])
    if meta.genres:
        tags.setall("TCON", [TCON(encoding=3, text=meta.genres)])

    audio.save()


def _write_mp4(file_path: Path, meta: AudiobookCandidate) -> None:
    audio = MP4(file_path)

    audio["\xa9nam"] = meta.title
    if meta.authors:
        audio["\xa9ART"] = meta.authors
    if meta.narrators:
        audio["aART"] = meta.narrators  # album artist atom, same convention as mp3
    if meta.series:
        audio["\xa9alb"] = meta.series
    if meta.published_date:
        audio["\xa9day"] = str(meta.published_date.year)
    if meta.genres:
        audio["\xa9gen"] = meta.genres
    if meta.description:
        audio["desc"] = meta.description

    audio.save()
