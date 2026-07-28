from datetime import datetime

from pydantic import BaseModel

from app.changes import ChangeSummary
from app.project_status import get_project_statuses

MAX_RECENT_WORK_LIMIT = 100


class RecentWorkItem(BaseModel):
    project_path: str
    project_name: str
    change: ChangeSummary


def _parse_updated(updated: str) -> datetime | None:
    try:
        return datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_recent_work(limit: int = 10) -> list[RecentWorkItem]:
    if not 1 <= limit <= MAX_RECENT_WORK_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_RECENT_WORK_LIMIT}")

    dated_items: list[tuple[datetime, RecentWorkItem]] = []
    undated_items: list[RecentWorkItem] = []
    for project in get_project_statuses():
        for change in project.changes:
            item = RecentWorkItem(
                project_path=project.path,
                project_name=project.name,
                change=change,
            )
            updated_at = _parse_updated(change.updated)
            if updated_at is None:
                undated_items.append(item)
            else:
                dated_items.append((updated_at, item))

    dated_items.sort(key=lambda entry: entry[0], reverse=True)
    return ([item for _, item in dated_items] + undated_items)[:limit]