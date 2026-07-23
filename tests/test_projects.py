from pathlib import Path

import pytest

from app import projects


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "DATA_FILE", tmp_path / "data" / "tracked_projects.json")


def _make_project(tmp_path: Path, name: str) -> Path:
    project = tmp_path / name
    (project / "context" / "changes").mkdir(parents=True)
    return project


def test_valid_path_accepted(tmp_path: Path) -> None:
    project = _make_project(tmp_path, "good-project")

    assert projects.validate_project_path(project) == project


def test_path_without_context_changes_rejected(tmp_path: Path) -> None:
    project = tmp_path / "bad-project"
    project.mkdir()

    with pytest.raises(ValueError):
        projects.validate_project_path(project)


def test_duplicate_path_rejected(tmp_path: Path) -> None:
    project = _make_project(tmp_path, "dup-project")

    projects.add_tracked_project(project)

    with pytest.raises(ValueError):
        projects.add_tracked_project(project)


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    project_a = _make_project(tmp_path, "project-a")
    project_b = _make_project(tmp_path, "project-b")

    projects.save_tracked_projects([project_a, project_b])
    loaded = projects.load_tracked_projects()

    assert loaded == [project_a, project_b]


def test_remove_tracked_project_removes_it(tmp_path: Path) -> None:
    project_a = _make_project(tmp_path, "project-a")
    project_b = _make_project(tmp_path, "project-b")
    projects.add_tracked_project(project_a)
    projects.add_tracked_project(project_b)

    projects.remove_tracked_project(project_a)

    loaded = projects.load_tracked_projects()
    assert loaded == [project_b.resolve()]


def test_remove_untracked_project_raises(tmp_path: Path) -> None:
    project = _make_project(tmp_path, "never-added")

    with pytest.raises(ValueError):
        projects.remove_tracked_project(project)


def test_remove_tracked_project_is_case_insensitive(tmp_path: Path) -> None:
    project = _make_project(tmp_path, "Case-Project")
    projects.add_tracked_project(project)

    differently_cased = Path(str(project).upper())
    projects.remove_tracked_project(differently_cased)

    assert projects.load_tracked_projects() == []
