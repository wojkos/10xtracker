import subprocess
from pathlib import Path

from app.changes import ChangeSummary, list_changes

BRANCH_REF_PREFIX = "refs/heads/"


def _parse_worktree_blocks(output: str) -> list[dict[str, str | None]]:
    blocks: list[dict[str, str | None]] = []
    current: dict[str, str | None] = {}
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append(current)
                current = {}
            continue
        if stripped.startswith("worktree "):
            if current:
                blocks.append(current)
            current = {"path": stripped[len("worktree ") :]}
        elif stripped == "detached":
            current["branch"] = None
        elif stripped.startswith("branch "):
            ref = stripped[len("branch ") :]
            current["branch"] = (
                ref[len(BRANCH_REF_PREFIX) :] if ref.startswith(BRANCH_REF_PREFIX) else ref
            )
        # else: ignore HEAD, locked, bare, prunable, and any other line we don't recognize
    if current:
        blocks.append(current)
    return blocks


def list_project_worktrees(project_path: Path) -> list[tuple[Path, str | None]]:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_path), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    main_path = project_path.resolve()
    worktrees: list[tuple[Path, str | None]] = []
    for block in _parse_worktree_blocks(result.stdout):
        raw_path = block.get("path")
        if raw_path is None:
            continue
        path = Path(raw_path).resolve()
        if path == main_path:
            continue
        worktrees.append((path, block.get("branch")))
    return worktrees


def get_worktree_branch_map(
    project_path: Path, change_ids: set[str]
) -> dict[str, tuple[str | None, ChangeSummary]]:
    branch_map: dict[str, tuple[str | None, ChangeSummary]] = {}
    for worktree_path, branch in list_project_worktrees(project_path):
        for summary in list_changes(worktree_path / "context"):
            if summary.change_id not in change_ids or summary.change_id in branch_map:
                continue
            branch_map[summary.change_id] = (branch, summary)
    return branch_map
