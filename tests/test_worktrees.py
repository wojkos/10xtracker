import subprocess
from pathlib import Path

from app.worktrees import get_worktree_branch_map, list_project_worktrees


def _run_git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _run_git("init", cwd=path)
    _run_git("config", "user.email", "test@example.com", cwd=path)
    _run_git("config", "user.name", "Test", cwd=path)
    (path / "README.md").write_text("placeholder\n", encoding="utf-8")
    _run_git("add", "README.md", cwd=path)
    _run_git("commit", "-m", "initial commit", cwd=path)


def _write_change_md(changes_dir: Path, change_id: str, status: str = "implementing") -> None:
    folder = changes_dir / change_id
    folder.mkdir(parents=True)
    (folder / "change.md").write_text(
        f"""---
change_id: {change_id}
title: {change_id}
status: {status}
created: 2026-07-23
updated: 2026-07-23
archived_at: null
---
""",
        encoding="utf-8",
    )


def test_list_project_worktrees_returns_empty_for_non_git_directory(tmp_path: Path) -> None:
    project = tmp_path / "not-a-repo"
    project.mkdir()

    assert list_project_worktrees(project) == []


def test_get_worktree_branch_map_returns_empty_for_non_git_directory(tmp_path: Path) -> None:
    project = tmp_path / "not-a-repo"
    project.mkdir()

    assert get_worktree_branch_map(project, {"some-change"}) == {}


def test_list_project_worktrees_returns_empty_when_no_linked_worktrees(tmp_path: Path) -> None:
    project = tmp_path / "solo-repo"
    _init_git_repo(project)

    assert list_project_worktrees(project) == []


def test_list_project_worktrees_finds_linked_worktree_with_branch(tmp_path: Path) -> None:
    project = tmp_path / "main-repo"
    _init_git_repo(project)
    worktree_path = tmp_path / "linked-worktree"
    _run_git("worktree", "add", str(worktree_path), "-b", "feature-branch", cwd=project)

    worktrees = list_project_worktrees(project)

    assert len(worktrees) == 1
    path, branch = worktrees[0]
    assert path == worktree_path.resolve()
    assert branch == "feature-branch"


def test_get_worktree_branch_map_correlates_matching_change_id(tmp_path: Path) -> None:
    project = tmp_path / "main-repo"
    _init_git_repo(project)
    worktree_path = tmp_path / "linked-worktree"
    _run_git("worktree", "add", str(worktree_path), "-b", "feature-branch", cwd=project)
    _write_change_md(worktree_path / "context" / "changes", "matching-change")

    branch_map = get_worktree_branch_map(project, {"matching-change"})

    assert set(branch_map) == {"matching-change"}
    branch, summary = branch_map["matching-change"]
    assert branch == "feature-branch"
    assert summary.change_id == "matching-change"
    assert summary.status == "implementing"


def test_get_worktree_branch_map_ignores_change_id_not_in_requested_set(tmp_path: Path) -> None:
    project = tmp_path / "main-repo"
    _init_git_repo(project)
    worktree_path = tmp_path / "linked-worktree"
    _run_git("worktree", "add", str(worktree_path), "-b", "feature-branch", cwd=project)
    _write_change_md(worktree_path / "context" / "changes", "unrelated-change")

    branch_map = get_worktree_branch_map(project, {"matching-change"})

    assert branch_map == {}
