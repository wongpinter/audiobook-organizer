"""Core domain models. No I/O, no provider/TUI/tagging concerns here."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field


class Query(BaseModel):
    """What the user is searching for."""

    title: str
    author: str | None = None


class AudiobookCandidate(BaseModel):
    """A single metadata match returned by a provider."""

    source_name: str
    source_id: str  # ASIN, ISBN, OLID, or provider-internal id

    title: str
    subtitle: str | None = None
    authors: list[str] = Field(default_factory=list)
    narrators: list[str] = Field(default_factory=list)

    series: str | None = None
    series_index: float | None = None

    published_date: date | None = None
    publisher: str | None = None

    description: str | None = None
    genres: list[str] = Field(default_factory=list)

    duration_seconds: int | None = None
    cover_url: str | None = None

    # Filled in by the scoring layer, not the provider itself.
    match_score: float = 0.0

    def author_display(self) -> str:
        """'Lastname, Firstname' for the first author, for filename patterns."""
        if not self.authors:
            return "Unknown"
        parts = self.authors[0].rsplit(" ", 1)
        return f"{parts[-1]}, {parts[0]}" if len(parts) == 2 else self.authors[0]


class RenamePlan(BaseModel):
    """One row in the batch review screen: an old path mapped to a proposed new path."""

    old_path: Path
    new_path: Path | None  # None means "no confident match, skipped by default"
    metadata: AudiobookCandidate | None = None
    include: bool = True
    reason_skipped: str | None = None
    chapter_title: str | None = None
    track_number: int | None = None
    disc_number: int | None = None

    class Config:
        arbitrary_types_allowed = True


class RenameManifestEntry(BaseModel):
    """One committed rename, written to disk before the actual move happens."""

    old_path: Path
    new_path: Path
    timestamp: str
    moved: bool = False
    tag_status: str = "pending"
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True


class BatchManifest(BaseModel):
    batch_id: str
    created_at: str
    mode: str = "move"
    entries: list[RenameManifestEntry] = Field(default_factory=list)
    rollback_errors: list[str] = Field(default_factory=list)
    undone: bool = False

    class Config:
        arbitrary_types_allowed = True
