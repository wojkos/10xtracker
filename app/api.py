from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.changes import ChangeSummary, list_changes
from app.projects import add_tracked_project, load_tracked_projects

router = APIRouter()


class AddProjectRequest(BaseModel):
    path: str


class ProjectResponse(BaseModel):
    path: str
    name: str
    changes: list[ChangeSummary]


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
