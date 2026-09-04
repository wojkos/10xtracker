from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import projects, settings
from app.main import app
from app.project_status import get_project_status


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "DATA_FILE", tmp_path / "data" / "tracked_projects.json")
    monkeypatch.setattr(settings, "DATA_FILE", tmp_path / "data" / "settings.json")


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


def _make_fixture_project_with_plan(tmp_path: Path) -> Path:
    project = tmp_path / "fixture-project-with-plan"
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
    (change_folder / "plan.md").write_text(
        """## Progress

### Phase 1: Only phase

#### Automated

- [x] 1.1 First step — abc1234
- [ ] 1.2 Second step
""",
        encoding="utf-8",
    )
    return project


def _make_fixture_project_with_roadmap(tmp_path: Path) -> Path:
    project = tmp_path / "fixture-project-with-roadmap"
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
    foundation_dir = project / "context" / "foundation"
    foundation_dir.mkdir(parents=True)
    (foundation_dir / "roadmap.md").write_text(
        """## At a glance

| ID   | Change ID   | Outcome (user can ...) | Prerequisites | PRD refs | Status |
| ---- | ----------- | ----------------------- | -------------- | -------- | ------ |
| S-04 | some-change | do the thing            | -              | -        | done   |
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


def test_post_project_response_matches_shared_project_status_service(
    client: TestClient, tmp_path: Path
) -> None:
    project = _make_fixture_project(tmp_path)

    response = client.post("/api/projects", json={"path": str(project)})

    assert response.status_code == 200
    assert response.json() == get_project_status(project.resolve()).model_dump(mode="json")


def test_post_response_includes_phase_progress(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project_with_plan(tmp_path)

    response = client.post("/api/projects", json={"path": str(project)})

    assert response.status_code == 200
    body = response.json()
    phase_progress = body["changes"][0]["phase_progress"]
    assert phase_progress == {"phase_number": 1, "done": 1, "total": 2}


def test_get_response_includes_phase_progress(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project_with_plan(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.get("/api/projects")

    assert response.status_code == 200
    body = response.json()
    phase_progress = body[0]["changes"][0]["phase_progress"]
    assert phase_progress == {"phase_number": 1, "done": 1, "total": 2}


def test_post_response_includes_roadmap_correlation(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project_with_roadmap(tmp_path)

    response = client.post("/api/projects", json={"path": str(project)})

    assert response.status_code == 200
    body = response.json()
    roadmap_correlation = body["changes"][0]["roadmap_correlation"]
    assert roadmap_correlation == {
        "roadmap_id": "S-04",
        "outcome": "do the thing",
        "prerequisites": [],
        "status": "done",
        "order": 0,
    }


def test_get_response_includes_roadmap_correlation(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project_with_roadmap(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.get("/api/projects")

    assert response.status_code == 200
    body = response.json()
    roadmap_correlation = body[0]["changes"][0]["roadmap_correlation"]
    assert roadmap_correlation == {
        "roadmap_id": "S-04",
        "outcome": "do the thing",
        "prerequisites": [],
        "status": "done",
        "order": 0,
    }


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


def _make_fixture_project_with_update_date(tmp_path: Path, name: str, updated: str) -> Path:
    project = tmp_path / name
    change_folder = project / "context" / "changes" / "some-change"
    change_folder.mkdir(parents=True)
    (change_folder / "change.md").write_text(
        f"""---
change_id: some-change
title: Some Change
status: implementing
created: {updated}
updated: {updated}
archived_at: null
---
""",
        encoding="utf-8",
    )
    return project


def test_get_orders_projects_by_most_recently_updated_change(
    client: TestClient, tmp_path: Path
) -> None:
    older = _make_fixture_project_with_update_date(tmp_path, "older-project", "2026-01-01")
    newer = _make_fixture_project_with_update_date(tmp_path, "newer-project", "2026-06-15")
    client.post("/api/projects", json={"path": str(older)})
    client.post("/api/projects", json={"path": str(newer)})

    response = client.get("/api/projects")

    assert [p["name"] for p in response.json()] == ["newer-project", "older-project"]


def test_get_after_post_returns_project_in_list(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.get("/api/projects")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "fixture-project"


def test_delete_after_post_removes_project(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.request("DELETE", "/api/projects", json={"path": str(project)})

    assert response.status_code == 200
    list_response = client.get("/api/projects")
    assert list_response.json() == []


def test_delete_never_added_path_returns_404(client: TestClient, tmp_path: Path) -> None:
    project = _make_fixture_project(tmp_path)

    response = client.request("DELETE", "/api/projects", json={"path": str(project)})

    assert response.status_code == 404
    assert "detail" in response.json()


def test_get_settings_returns_defaults_when_nothing_saved(client: TestClient) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "interval_minutes": 5}


def test_put_settings_with_valid_payload_returns_saved_values(client: TestClient) -> None:
    response = client.put(
        "/api/settings", json={"enabled": True, "interval_minutes": 10}
    )

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "interval_minutes": 10}


def test_get_settings_after_put_reflects_update(client: TestClient) -> None:
    client.put("/api/settings", json={"enabled": True, "interval_minutes": 10})

    response = client.get("/api/settings")

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "interval_minutes": 10}


def test_put_settings_with_out_of_range_interval_returns_400(client: TestClient) -> None:
    response = client.put(
        "/api/settings", json={"enabled": True, "interval_minutes": 0}
    )

    assert response.status_code == 400
    assert "detail" in response.json()


def test_get_recommendations_returns_high_confidence_entry(
    client: TestClient, tmp_path: Path
) -> None:
    project = _make_fixture_project_with_plan(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.get("/api/recommendations")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["confidence"] == "high"
    assert body[0]["command"] == "/10x-implement some-change phase 1"
    assert body[0]["reason"]


def test_get_recommendations_returns_low_confidence_entry(
    client: TestClient, tmp_path: Path
) -> None:
    project = _make_fixture_project(tmp_path)
    client.post("/api/projects", json={"path": str(project)})

    response = client.get("/api/recommendations")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["confidence"] == "low"
    assert body[0]["command"] is None
    assert body[0]["blocking_question"]
    assert body[0]["candidates"] == ["some-change"]
