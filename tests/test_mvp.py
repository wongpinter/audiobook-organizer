from datetime import date
from pathlib import Path

import pytest

from audiobook_fetcher.config import load_config
from audiobook_fetcher.domain.models import AudiobookCandidate
from audiobook_fetcher.input.scanner import parse_filename, scan_directory
from audiobook_fetcher.rename.manifest import commit_batch, undo
from audiobook_fetcher.rename.plan_store import load_plan, save_plan
from audiobook_fetcher.rename.planner import build_plan


def meta(title="Book", author="Jane Doe"):
    return AudiobookCandidate(source_name="test", source_id="1", title=title, authors=[author], published_date=date(2020, 1, 1))


def test_scan_is_nonrecursive_and_parses_names(tmp_path: Path):
    (tmp_path / "Z - Last.m4b").touch()
    (tmp_path / "title-only.mp3").touch()
    (tmp_path / ".hidden.m4a").touch()
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "ignored.mp3").touch()
    assert [p.name for p in scan_directory(tmp_path)] == ["title-only.mp3", "Z - Last.m4b"]
    assert parse_filename(Path("A - B - C.mp3")).author == "A"
    assert parse_filename(Path("A - B - C.mp3")).title == "B - C"
    assert parse_filename(Path("title-only.mp3")).author is None


def test_config_cli_values_override_toml(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text('input_dir = "toml-in"\noutput_root = "toml-out"\npattern = "toml"\n')
    config = load_config(config_file, input_dir=tmp_path / "cli-in", pattern="cli")
    assert config.input_dir == tmp_path / "cli-in"
    assert config.output_root == Path("toml-out")
    assert config.pattern == "cli"


def test_planner_blocks_collision_and_same_path_is_excluded(tmp_path: Path):
    source = tmp_path / "old.mp3"
    source.touch()
    plans = build_plan([(source, meta())], output_root=tmp_path)
    assert plans[0].include
    assert plans[0].new_path != source.resolve()
    same = build_plan([(source, AudiobookCandidate(source_name="x", source_id="x", title="old", authors=["Doe, Jane"]))], pattern="{original_name}", output_root=tmp_path)
    assert not same[0].include


def test_commit_and_undo_roundtrip(tmp_path: Path):
    source = tmp_path / "old.mp3"
    source.write_bytes(b"x")
    plans = build_plan([(source, meta())], output_root=tmp_path / "out")
    manifest = tmp_path / ".app" / "manifest.json"
    commit_batch(plans, manifest)
    assert not source.exists()
    destination = plans[0].new_path
    assert destination.exists()
    undo(manifest)
    assert source.exists()
    assert not destination.exists()


def test_commit_blocks_existing_destination(tmp_path: Path):
    source = tmp_path / "old.mp3"
    source.touch()
    output = tmp_path / "out"
    plans = build_plan([(source, meta())], output_root=output)
    plans[0].new_path.parent.mkdir(parents=True)
    plans[0].new_path.touch()
    with pytest.raises(FileExistsError):
        commit_batch(plans, tmp_path / "manifest.json")
    assert source.exists()


def test_plan_store_roundtrip(tmp_path: Path):
    source = tmp_path / "old.mp3"
    source.touch()
    plans = build_plan([(source, meta())], output_root=tmp_path / "out")
    path = save_plan(plans, tmp_path / "plan.json")
    loaded = load_plan(path)
    assert loaded[0].old_path == source
    assert loaded[0].metadata.title == "Book"
