from pathlib import Path

from pydantic import BaseModel, Field

from app.plan_progress import get_phase_progress
from app.project_status import ProjectResponse, get_project_statuses
from app.roadmap_correlation import RoadmapCorrelation, get_roadmap_correlations

COMPLETE_ROADMAP_STATUSES = {"complete", "completed", "done"}
ACTIVE_CHANGE_STATUSES = {"new", "preparing", "planned", "plan_reviewed", "implementing", "implemented"}


class WorkflowRecommendation(BaseModel):
    project_path: str
    change_id: str | None = None
    command: str | None = None
    reason: str
    confidence: str
    alternatives: list[str] = Field(default_factory=list)
    candidates: list[str] = Field(default_factory=list)
    blocking_question: str | None = None


def _blocked(
    project: ProjectResponse, reason: str, *, candidates: list[str] | None = None
) -> WorkflowRecommendation:
    return WorkflowRecommendation(
        project_path=project.path,
        reason=reason,
        confidence="low",
        candidates=candidates or [],
        blocking_question="Which change should be worked on next?",
    )


def _is_complete(status: str) -> bool:
    return status.strip().lower() in COMPLETE_ROADMAP_STATUSES


def _eligible_roadmap_change(
    project: ProjectResponse,
) -> tuple[str, RoadmapCorrelation] | None:
    correlations = get_roadmap_correlations(Path(project.path) / "context")
    if not correlations:
        return None

    roadmap_by_id = {correlation.roadmap_id: correlation for correlation in correlations.values()}
    for change_id, correlation in sorted(
        correlations.items(), key=lambda item: item[1].order
    ):
        prerequisites = [roadmap_by_id.get(item) for item in correlation.prerequisites]
        if not _is_complete(correlation.status) and all(
            prerequisite is not None and _is_complete(prerequisite.status)
            for prerequisite in prerequisites
        ):
            return change_id, correlation
    return None


def _recommend_for_active_change(
    project: ProjectResponse, change_id: str, status: str
) -> WorkflowRecommendation:
    change_dir = Path(project.path) / "context" / "changes" / change_id
    has_research_or_frame = (change_dir / "research.md").is_file() or (
        change_dir / "frame.md"
    ).is_file()
    has_plan = (change_dir / "plan.md").is_file()
    has_plan_review = (change_dir / "reviews" / "plan-review.md").is_file()

    if status == "new" and not has_research_or_frame and not has_plan:
        return WorkflowRecommendation(
            project_path=project.path,
            change_id=change_id,
            command=f"/10x-research {change_id}",
            reason="The new change has no research or framing context.",
            confidence="high",
        )
    if status in {"new", "preparing"} and has_research_or_frame and not has_plan:
        return WorkflowRecommendation(
            project_path=project.path,
            change_id=change_id,
            command=f"/10x-plan {change_id}",
            reason="The change has context but no implementation plan.",
            confidence="high",
        )
    if status == "planned" and has_plan and not has_plan_review:
        return WorkflowRecommendation(
            project_path=project.path,
            change_id=change_id,
            command=f"/10x-plan-review {change_id}",
            reason="The planned change has no plan-review artifact.",
            confidence="high",
        )

    if status in {"plan_reviewed", "implementing", "implemented"} and has_plan:
        phase_progress = get_phase_progress(change_dir)
        if phase_progress is None:
            return _blocked(project, "The implementation-ready change has no readable plan progress.")
        if phase_progress.done < phase_progress.total:
            return WorkflowRecommendation(
                project_path=project.path,
                change_id=change_id,
                command=f"/10x-implement {change_id} phase {phase_progress.phase_number}",
                reason="The plan has unchecked progress items.",
                confidence="high",
                alternatives=[
                    f"/10x-tdd {change_id}",
                    f"/10x-e2e {change_id}",
                    f"/10x-goal-implement {change_id} phase {phase_progress.phase_number}",
                ],
            )
        return WorkflowRecommendation(
            project_path=project.path,
            change_id=change_id,
            command=f"/10x-impl-review {change_id}",
            reason="All plan-progress items are checked.",
            confidence="high",
            alternatives=[f"/10x-archive {change_id}"],
        )

    return _blocked(
        project,
        "The change status and available artifacts do not support a safe recommendation.",
        candidates=[change_id],
    )


def get_next_10x_action(project_path: str | None = None) -> list[WorkflowRecommendation]:
    projects = get_project_statuses()
    if project_path is not None:
        projects = [project for project in projects if project.path == project_path]

    recommendations: list[WorkflowRecommendation] = []
    for project in projects:
        malformed_changes = [change.change_id for change in project.changes if change.error]
        if malformed_changes:
            recommendations.append(
                _blocked(
                    project,
                    "A change record is malformed and must be corrected before choosing work.",
                    candidates=malformed_changes,
                )
            )
            continue

        active_changes = [
            change
            for change in project.changes
            if change.status.strip().lower() in ACTIVE_CHANGE_STATUSES
        ]
        unsupported_changes = [
            change.change_id
            for change in project.changes
            if change.status.strip().lower() not in ACTIVE_CHANGE_STATUSES
            and change.status.strip().lower() not in {"archived", "complete", "completed"}
        ]
        if unsupported_changes:
            recommendations.append(
                _blocked(
                    project,
                    "A change has an unsupported lifecycle status.",
                    candidates=unsupported_changes,
                )
            )
        elif len(active_changes) > 1:
            recommendations.append(
                _blocked(
                    project,
                    "Multiple active changes make the next action ambiguous.",
                    candidates=[change.change_id for change in active_changes],
                )
            )
        elif len(active_changes) == 1:
            active_change = active_changes[0]
            recommendations.append(
                _recommend_for_active_change(
                    project, active_change.change_id, active_change.status.strip().lower()
                )
            )
        else:
            eligible_roadmap_change = _eligible_roadmap_change(project)
            if eligible_roadmap_change is None:
                recommendations.append(
                    _blocked(
                        project,
                        "No roadmap slice can be proven eligible from the available metadata.",
                    )
                )
            else:
                change_id, _ = eligible_roadmap_change
                recommendations.append(
                    WorkflowRecommendation(
                        project_path=project.path,
                        change_id=change_id,
                        command=f"/10x-new {change_id}",
                        reason="This is the earliest incomplete roadmap slice with complete prerequisites.",
                        confidence="high",
                    )
                )
    return recommendations