"""Thin command-line integration for planning, committing, and undoing moves."""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from audiobook_fetcher.config import load_config
from audiobook_fetcher.input.scanner import parse_filename, scan_directory
from audiobook_fetcher.providers.orchestrator import search_all
from audiobook_fetcher.tagging.reader import read_metadata
from audiobook_fetcher.rename.manifest import commit_batch, tag_manifest, undo
from audiobook_fetcher.rename.plan_store import load_plan, save_plan
from audiobook_fetcher.rename.planner import build_plan
from audiobook_fetcher.tui.batch_review import review_batch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audiobook-fetcher")
    parser.add_argument("--config", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("input_dir", nargs="?", type=Path)
    plan.add_argument("--output-root", type=Path)
    plan.add_argument("--pattern")
    plan.add_argument("--plan-file", type=Path)
    plan.add_argument("--source", choices=("openlibrary", "tags"), default="openlibrary")
    commit = sub.add_parser("commit")
    commit.add_argument("plan_file", type=Path)
    commit.add_argument("--manifest", type=Path)
    undo_cmd = sub.add_parser("undo")
    undo_cmd.add_argument("manifest", type=Path)
    return parser


async def _make_plans(input_dir: Path, pattern: str, output_root: Path, source: str):
    rows = []
    for path in scan_directory(input_dir):
        if source == "tags":
            try:
                metadata, chapter, track, disc = read_metadata(path)
                rows.append((path, metadata, chapter, track, disc))
            except Exception:
                rows.append((path, None))
        else:
            matches = await search_all(parse_filename(path))
            rows.append((path, matches[0] if matches else None))
    return build_plan(rows, pattern=pattern, output_root=output_root)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    overrides = {}
    if getattr(args, "input_dir", None) is not None:
        overrides["input_dir"] = args.input_dir
    if getattr(args, "output_root", None) is not None:
        overrides["output_root"] = args.output_root
    if getattr(args, "pattern", None) is not None:
        overrides["pattern"] = args.pattern
    config = load_config(args.config, **overrides)
    if args.command == "plan":
        plans = asyncio.run(_make_plans(config.input_dir, config.pattern, config.output_root, args.source))
        approved = review_batch(plans)
        if approved is None:
            return 1
        path = args.plan_file or config.resolved_manifest_dir.parent / "plans" / "approved.json"
        save_plan(approved, path)
        print(path)
        return 0
    if args.command == "commit":
        plans = load_plan(args.plan_file)
        manifest = args.manifest or config.resolved_manifest_dir / f"{args.plan_file.stem}.json"
        commit_batch(plans, manifest)
        failures = tag_manifest(manifest, plans)
        for failure in failures:
            print(f"tag failure: {failure}")
        print(manifest)
        return 0
    undo(args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
