from pathlib import Path

from pydantic import BaseModel

from app.changes import ChangeSummary, list_changes
from app.projects import load_tracked_projects
from app.worktrees import get_worktree_branch_map


class ProjectResponse(BaseModel):
    path: str
    name: str
    changes: list[ChangeSummary]


class ProjectSummary(BaseModel):
    path: str
    name: str


def get_project_status(project_path: Path) -> ProjectResponse:
    changes = list_changes(project_path / "context")
    branch_map = get_worktree_branch_map(project_path, {change.change_id for change in changes})
    changes = [
        branch_map[change.change_id][1].model_copy(
            update={"branch": branch_map[change.change_id][0]}
        )
        if change.change_id in branch_map
        else change
        for change in changes
    ]
    return ProjectResponse(
        path=str(project_path),
        name=project_path.name,
        changes=changes,
    )


def _latest_update(project: ProjectResponse) -> str:
    return max((c.updated for c in project.changes if c.updated and not c.error), default="")


def get_project_statuses() -> list[ProjectResponse]:
    statuses = [
        get_project_status(entry.path)
        for entry in load_tracked_projects()
        if entry.active
    ]
    return sorted(statuses, key=_latest_update, reverse=True)


def get_inactive_projects() -> list[ProjectSummary]:
    return [
        ProjectSummary(path=str(entry.path), name=entry.path.name)
        for entry in load_tracked_projects()
        if not entry.active
    ]
