from pathlib import Path

import pytest

from app import projects
from app.recent_work import get_recent_work


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "DATA_FILE", tmp_path / "data" / "tracked_projects.json")


def _make_project(tmp_path: Path, name: str, changes: list[tuple[str, str]]) -> Path:
    project = tmp_path / name
    changes_dir = project / "context" / "changes"
    for change_id, updated in changes:
        change_dir = changes_dir / change_id
        change_dir.mkdir(parents=True)
        (change_dir / "change.md").write_text(
            f"""---
change_id: {change_id}
title: {change_id}
status: planned
updated: {updated}
---
""",
            encoding="utf-8",
        )
    return project


def test_returns_tracked_changes_in_descending_updated_order(tmp_path: Path) -> None:
    first = _make_project(tmp_path, "first", [("older", "2026-07-01")])
    second = _make_project(tmp_path, "second", [("newer", "2026-07-02T12:00:00")])
    projects.save_tracked_projects([first, second])

    recent_work = get_recent_work()

    assert [item.change.change_id for item in recent_work] == ["newer", "older"]
    assert recent_work[0].project_path == str(second)
    assert recent_work[0].project_name == "second"


def test_invalid_or_missing_dates_follow_dated_records(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        "fixture",
        [("dated", "2026-07-02"), ("invalid", "not-a-date"), ("missing", "")],
    )
    projects.save_tracked_projects([project])

    recent_work = get_recent_work()

    assert [item.change.change_id for item in recent_work] == ["dated", "invalid", "missing"]
    assert recent_work[2].change.error == "missing required field(s): updated"


def test_limit_is_bounded_and_positive(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        "fixture",
        [("first", "2026-07-01"), ("second", "2026-07-02")],
    )
    projects.save_tracked_projects([project])

    assert [item.change.change_id for item in get_recent_work(limit=1)] == ["second"]
    with pytest.raises(ValueError, match="between 1 and 100"):
        get_recent_work(limit=0)
    with pytest.raises(ValueError, match="between 1 and 100"):
        get_recent_work(limit=101)


def test_uses_only_persisted_tracked_projects(tmp_path: Path) -> None:
    tracked = _make_project(tmp_path, "tracked", [("visible", "2026-07-02")])
    _make_project(tmp_path, "untracked", [("hidden", "2026-07-03")])
    projects.save_tracked_projects([tracked])

    recent_work = get_recent_work()

    assert [item.change.change_id for item in recent_work] == ["visible"]