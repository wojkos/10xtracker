from pathlib import Path

import pytest

from app import project_status, projects
from app.changes import list_changes
from app.projects import TrackedProject
from app.workflow_recommendations import get_next_10x_action


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "DATA_FILE", tmp_path / "data" / "tracked_projects.json")


def _stub_worktree_branch(monkeypatch: pytest.MonkeyPatch, change_id: str, branch: str) -> None:
    def fake(project_path: Path, change_ids: set[str]):
        if change_id not in change_ids:
            return {}
        for summary in list_changes(project_path / "context"):
            if summary.change_id == change_id:
                return {change_id: (branch, summary)}
        return {}

    monkeypatch.setattr(project_status, "get_worktree_branch_map", fake)


def _make_project(
    tmp_path: Path,
    change_specs: list[tuple[str, str, set[str]]],
    roadmap: str | None = None,
) -> Path:
    project = tmp_path / "fixture"
    changes_dir = project / "context" / "changes"
    for change_id, status, artifacts in change_specs:
        change_dir = changes_dir / change_id
        change_dir.mkdir(parents=True)
        (change_dir / "change.md").write_text(
            f"""---
change_id: {change_id}
title: {change_id}
status: {status}
updated: 2026-07-28
---
""",
            encoding="utf-8",
        )
        if "research" in artifacts:
            (change_dir / "research.md").write_text("# Research\n", encoding="utf-8")
        if "plan" in artifacts:
            (change_dir / "plan.md").write_text(
                """## Progress

### Phase 1: Build

#### Automated

- [ ] 1.1 Work
""",
                encoding="utf-8",
            )
        if "complete-plan" in artifacts:
            (change_dir / "plan.md").write_text(
                """## Progress

### Phase 1: Build

#### Automated

- [x] 1.1 Work
""",
                encoding="utf-8",
            )
        if "review" in artifacts:
            reviews_dir = change_dir / "reviews"
            reviews_dir.mkdir()
            (reviews_dir / "plan-review.md").write_text("# Review\n", encoding="utf-8")
    if roadmap is not None:
        foundation_dir = project / "context" / "foundation"
        foundation_dir.mkdir(parents=True)
        (foundation_dir / "roadmap.md").write_text(roadmap, encoding="utf-8")
    projects.save_tracked_projects([TrackedProject(path=project)])
    return project


def test_new_change_without_context_recommends_research(tmp_path: Path) -> None:
    _make_project(tmp_path, [("change", "new", set())])

    recommendation = get_next_10x_action()[0]

    assert recommendation.command == "/10x-research change"


def test_context_without_plan_recommends_planning(tmp_path: Path) -> None:
    _make_project(tmp_path, [("change", "preparing", {"research"})])

    assert get_next_10x_action()[0].command == "/10x-plan change"


def test_planned_change_without_review_recommends_plan_review(tmp_path: Path) -> None:
    _make_project(tmp_path, [("change", "planned", {"plan"})])

    assert get_next_10x_action()[0].command == "/10x-plan-review change"


def test_incomplete_reviewed_plan_recommends_implementation_with_alternatives(
    tmp_path: Path,
) -> None:
    _make_project(tmp_path, [("change", "plan_reviewed", {"plan", "review"})])

    recommendation = get_next_10x_action()[0]

    assert recommendation.command == "/10x-implement change phase 1"
    assert recommendation.alternatives == [
        "/10x-tdd change",
        "/10x-e2e change",
        "/10x-goal-implement change phase 1",
    ]


def test_completed_plan_recommends_implementation_review(tmp_path: Path) -> None:
    _make_project(tmp_path, [("change", "implementing", {"complete-plan"})])

    recommendation = get_next_10x_action()[0]

    assert recommendation.command == "/10x-impl-review change"
    assert recommendation.alternatives == ["/10x-archive change"]


def test_no_active_change_selects_earliest_eligible_roadmap_slice(tmp_path: Path) -> None:
    _make_project(
        tmp_path,
        [],
        """## At a glance

| ID | Change ID | Outcome | Prerequisites | PRD refs | Status |
| -- | --------- | ------- | ------------- | -------- | ------ |
| F-01 | foundation | Foundation | - | - | done |
| S-01 | eligible-change | Eligible | F-01 | - | proposed |
| S-02 | blocked-change | Blocked | S-01 | - | proposed |
""",
    )

    recommendation = get_next_10x_action()[0]

    assert recommendation.command == "/10x-new eligible-change"
    assert recommendation.change_id == "eligible-change"


def test_multiple_active_changes_block_a_command(tmp_path: Path) -> None:
    _make_project(tmp_path, [("first", "new", set()), ("second", "planned", {"plan"})])

    recommendation = get_next_10x_action()[0]

    assert recommendation.command is None
    assert recommendation.candidates == ["first", "second"]
    assert recommendation.blocking_question is not None


def test_single_active_change_with_worktree_returns_one_recommendation_with_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_project(tmp_path, [("change", "new", set())])
    _stub_worktree_branch(monkeypatch, "change", "feature-branch")

    recommendations = get_next_10x_action()

    assert len(recommendations) == 1
    assert recommendations[0].command == "/10x-research change"
    assert recommendations[0].branch == "feature-branch"


def test_malformed_change_blocks_a_command(tmp_path: Path) -> None:
    project = _make_project(tmp_path, [])
    malformed_dir = project / "context" / "changes" / "broken"
    malformed_dir.mkdir(parents=True)
    (malformed_dir / "change.md").write_text("not frontmatter", encoding="utf-8")

    recommendation = get_next_10x_action()[0]

    assert recommendation.command is None
    assert recommendation.candidates == ["broken"]
    assert recommendation.blocking_question is not None