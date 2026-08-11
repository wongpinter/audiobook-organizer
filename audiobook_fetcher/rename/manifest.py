"""Durable, preflighted batch moves with best-effort rollback and undo."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from audiobook_fetcher.domain.models import BatchManifest, RenameManifestEntry, RenamePlan
from audiobook_fetcher.tagging.writer import write_tags


def _included(plans: list[RenamePlan]) -> list[RenamePlan]:
    return [p for p in plans if p.include and p.new_path is not None]


def _preflight(plans: list[RenamePlan]) -> None:
    selected = _included(plans)
    destinations: set[Path] = set()
    errors: list[str] = []
    for plan in selected:
        old = plan.old_path.resolve()
        new = plan.new_path.resolve()
        if not old.exists():
            errors.append(f"missing source: {old}")
        if new in destinations:
            errors.append(f"duplicate destination: {new}")
        destinations.add(new)
        if new.exists():
            errors.append(f"destination exists: {new}")
        if new == old:
            errors.append(f"same source and destination: {old}")
    if errors:
        raise FileExistsError("batch preflight failed: " + "; ".join(errors))


def commit_batch(plans: list[RenamePlan], manifest_path: Path) -> Path:
    _preflight(plans)
    selected = _included(plans)
    now = datetime.now(timezone.utc).isoformat()
    manifest = BatchManifest(
        batch_id=uuid4().hex,
        created_at=now,
        entries=[RenameManifestEntry(old_path=p.old_path, new_path=p.new_path, timestamp=now) for p in selected],
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    moved: list[RenameManifestEntry] = []
    try:
        for entry in manifest.entries:
            entry.new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry.old_path), str(entry.new_path))
            entry.moved = True
            moved.append(entry)
    except Exception as exc:
        manifest.rollback_errors = [str(exc)]
        for entry in reversed(moved):
            try:
                shutil.move(str(entry.new_path), str(entry.old_path))
                entry.moved = False
            except Exception as rollback_exc:
                manifest.rollback_errors.append(f"rollback {entry.new_path}: {rollback_exc}")
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        raise
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest_path


def tag_manifest(manifest_path: Path, plans: list[RenamePlan]) -> list[str]:
    manifest = BatchManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    by_path = {p.new_path.resolve(): p for p in plans if p.new_path is not None}
    failures: list[str] = []
    for entry in manifest.entries:
        plan = by_path.get(entry.new_path.resolve())
        if not plan or not plan.metadata:
            continue
        try:
            write_tags(entry.new_path, plan.metadata)
            entry.tag_status = "ok"
        except Exception as exc:
            entry.tag_status = "failed"
            entry.error = str(exc)
            failures.append(f"{entry.new_path}: {exc}")
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return failures


def undo(manifest_path: Path) -> None:
    manifest = BatchManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if manifest.undone:
        return
    for entry in reversed(manifest.entries):
        if entry.new_path.exists():
            if entry.old_path.exists():
                raise FileExistsError(f"undo destination exists: {entry.old_path}")
            entry.old_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(entry.new_path), str(entry.old_path))
            entry.moved = False
    manifest.undone = True
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
