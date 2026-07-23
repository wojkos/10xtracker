from pathlib import Path

import yaml
from pydantic import BaseModel

REQUIRED_FIELDS = ("change_id", "title", "status", "updated")


class ChangeSummary(BaseModel):
    change_id: str
    title: str
    status: str
    updated: str
    error: str | None = None


def _extract_frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---' frontmatter delimiter")
    try:
        closing_index = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        raise ValueError("missing closing '---' frontmatter delimiter")
    frontmatter_text = "\n".join(lines[1:closing_index])
    data = yaml.safe_load(frontmatter_text)
    if not isinstance(data, dict):
        raise ValueError("frontmatter did not parse to a mapping")
    return data


def _parse_change_md(path: Path, change_id: str) -> ChangeSummary:
    try:
        data = _extract_frontmatter(path.read_text(encoding="utf-8"))
    except (ValueError, yaml.YAMLError) as exc:
        return ChangeSummary(
            change_id=change_id, title="", status="", updated="", error=str(exc)
        )

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        return ChangeSummary(
            change_id=change_id,
            title=str(data.get("title", "")),
            status=str(data.get("status", "")),
            updated=str(data.get("updated", "")),
            error=f"missing required field(s): {', '.join(missing)}",
        )

    return ChangeSummary(
        change_id=str(data["change_id"]),
        title=str(data["title"]),
        status=str(data["status"]),
        updated=str(data["updated"]),
    )


def list_changes(context_dir: Path) -> list[ChangeSummary]:
    changes_dir = context_dir / "changes"
    if not changes_dir.is_dir():
        return []

    summaries = []
    for entry in sorted(changes_dir.iterdir()):
        if not entry.is_dir():
            continue
        change_md = entry / "change.md"
        if not change_md.is_file():
            continue
        summaries.append(_parse_change_md(change_md, entry.name))
    return summaries
