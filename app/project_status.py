from pathlib import Path

from pydantic import BaseModel

from app.changes import ChangeSummary, list_changes
from app.projects import load_tracked_projects


class ProjectResponse(BaseModel):
    path: str
    name: str
    changes: list[ChangeSummary]


class ProjectSummary(BaseModel):
    path: str
    name: str


def get_project_status(project_path: Path) -> ProjectResponse:
    return ProjectResponse(
        path=str(project_path),
        name=project_path.name,
        changes=list_changes(project_path / "context"),
    )


def get_project_statuses() -> list[ProjectResponse]:
    return [
        get_project_status(entry.path)
        for entry in load_tracked_projects()
        if entry.active
    ]


def get_inactive_projects() -> list[ProjectSummary]:
    return [
        ProjectSummary(path=str(entry.path), name=entry.path.name)
        for entry in load_tracked_projects()
        if not entry.active
    ]