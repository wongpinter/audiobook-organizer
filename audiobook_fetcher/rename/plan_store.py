"""Durable approved plans consumed by `commit`."""
from __future__ import annotations

import json
from pathlib import Path

from audiobook_fetcher.domain.models import RenamePlan


def save_plan(plans: list[RenamePlan], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([p.model_dump(mode="json") for p in plans], indent=2), encoding="utf-8")
    return path


def load_plan(path: Path) -> list[RenamePlan]:
    return [RenamePlan.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]
