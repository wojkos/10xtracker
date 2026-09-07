from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.projects import (
    add_tracked_project,
    load_tracked_projects,
    remove_tracked_project,
    set_project_active,
)
from app.project_status import (
    ProjectResponse,
    ProjectSummary,
    get_inactive_projects,
    get_project_status,
    get_project_statuses,
)
from app.settings import load_autosync_settings, save_autosync_settings
from app.workflow_recommendations import WorkflowRecommendation, get_next_10x_action

router = APIRouter()


class ProjectPathRequest(BaseModel):
    path: str


class ProjectActiveRequest(BaseModel):
    path: str
    active: bool


class SettingsResponse(BaseModel):
    enabled: bool
    interval_minutes: int


class UpdateSettingsRequest(BaseModel):
    enabled: bool
    interval_minutes: int


@router.post("/projects", response_model=ProjectResponse)
def add_project(request: ProjectPathRequest) -> ProjectResponse:
    try:
        added_path = add_tracked_project(Path(request.path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return get_project_status(added_path)


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects() -> list[ProjectResponse]:
    return get_project_statuses()


@router.delete("/projects")
def remove_project(request: ProjectPathRequest) -> dict[str, bool]:
    try:
        remove_tracked_project(Path(request.path))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"removed": True}


@router.put("/projects/active")
def set_active(request: ProjectActiveRequest) -> dict[str, bool]:
    try:
        set_project_active(Path(request.path), request.active)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"active": request.active}


@router.get("/projects/inactive", response_model=list[ProjectSummary])
def list_inactive_projects() -> list[ProjectSummary]:
    return get_inactive_projects()


@router.get("/recommendations", response_model=list[WorkflowRecommendation])
def get_recommendations() -> list[WorkflowRecommendation]:
    return get_next_10x_action()


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
