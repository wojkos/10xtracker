from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.changes import ChangeSummary, list_changes
from app.projects import add_tracked_project, load_tracked_projects, remove_tracked_project
from app.settings import load_autosync_settings, save_autosync_settings

router = APIRouter()


class AddProjectRequest(BaseModel):
    path: str


class RemoveProjectRequest(BaseModel):
    path: str


class ProjectResponse(BaseModel):
    path: str
    name: str
    changes: list[ChangeSummary]


class SettingsResponse(BaseModel):
    enabled: bool
    interval_minutes: int


class UpdateSettingsRequest(BaseModel):
    enabled: bool
    interval_minutes: int


def _to_project_response(project_path: Path) -> ProjectResponse:
    changes = list_changes(project_path / "context")
    return ProjectResponse(
        path=str(project_path), name=project_path.name, changes=changes
    )


@router.post("/projects", response_model=ProjectResponse)
def add_project(request: AddProjectRequest) -> ProjectResponse:
    try:
        added_path = add_tracked_project(Path(request.path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_project_response(added_path)


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects() -> list[ProjectResponse]:
    return [_to_project_response(path) for path in load_tracked_projects()]


@router.delete("/projects")
def remove_project(request: RemoveProjectRequest) -> dict[str, bool]:
    try:
        remove_tracked_project(Path(request.path))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"removed": True}


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    enabled, interval_minutes = load_autosync_settings()
    return SettingsResponse(enabled=enabled, interval_minutes=interval_minutes)


@router.put("/settings", response_model=SettingsResponse)
def update_settings(request: UpdateSettingsRequest) -> SettingsResponse:
    try:
        save_autosync_settings(request.enabled, request.interval_minutes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return SettingsResponse(enabled=request.enabled, interval_minutes=request.interval_minutes)
