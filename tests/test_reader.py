from pathlib import Path

from audiobook_fetcher.domain.models import AudiobookCandidate
from audiobook_fetcher.rename.planner import build_plan
from audiobook_fetcher.tagging.reader import read_metadata


def test_read_metadata_maps_easy_tags(monkeypatch, tmp_path: Path):
    class Info:
        length = 3600

    class Audio:
        tags = {
            "title": "01 - The Beginning",
            "album": "My Audiobook",
            "artist": ["Author Name"],
            "tracknumber": ["1/12"],
            "date": ["2021"],
        }
        info = Info()

    monkeypatch.setattr("audiobook_fetcher.tagging.reader.File", lambda path, easy=True: Audio())
    candidate, chapter, track, disc = read_metadata(tmp_path / "chapter.mp3")
    assert candidate.title == "My Audiobook"
    assert candidate.authors == ["Author Name"]
    assert chapter == "01 - The Beginning"
    assert track == 1
    assert candidate.duration_seconds == 3600


def test_chapter_plan_groups_files_and_numbers_names(tmp_path: Path):
    first = tmp_path / "a.mp3"
    second = tmp_path / "b.mp3"
    first.touch()
    second.touch()
    candidate = AudiobookCandidate(source_name="embedded", source_id="book", title="Book", authors=["Author"])
    plans = build_plan(
        [
            (first, candidate, "Opening", 1, None),
            (second, candidate, "Ending", 2, None),
        ],
        output_root=tmp_path / "out",
    )
    assert plans[0].new_path.parent == plans[1].new_path.parent
    assert plans[0].new_path.name == "01 - Opening.mp3"
    assert plans[1].new_path.name == "02 - Ending.mp3"
