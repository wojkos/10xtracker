from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import projects
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "DATA_FILE", tmp_path / "data" / "tracked_projects.json")


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _make_fixture_project(tmp_path: Path) -> Path:
    project = tmp_path / "fixture-project"
    changes_dir = project / "context" / "changes"
    change_folder = changes_dir / "some-change"
    change_folder.mkdir(parents=True)
    (change_folder / "change.md").write_text(
        """---
change_id: some-change
title: Some Change
status: implementing
created: 2026-07-23
updated: 2026-07-23
archived_at: null
---
""",
        encoding="utf-8",
    )
    return project


def test_post_valid_path_returns_parsed_changes(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project(tmp_path)

    response = client.post("/api/projects", json={"path": str(project)})

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "fixture-project"
    assert len(body["changes"]) == 1
    assert body["changes"][0]["change_id"] == "some-change"
    assert body["changes"][0]["status"] == "implementing"


def test_post_path_without_context_changes_returns_400(
    client: TestClient, tmp_path: Path
) -> None:
    project = tmp_path / "not-a-project"
    project.mkdir()

    response = client.post("/api/projects", json={"path": str(project)})

    assert response.status_code == 400
    assert "detail" in response.json()


def test_post_duplicate_path_returns_400(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.post("/api/projects", json={"path": str(project)})

    assert response.status_code == 400


def test_get_after_post_returns_project_in_list(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.get("/api/projects")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "fixture-project"
