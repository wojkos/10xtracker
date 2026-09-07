import json
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path("data/tracked_projects.json")


@dataclass
class TrackedProject:
    path: Path
    active: bool = True


def validate_project_path(path: Path) -> Path:
    if not (path / "context" / "changes").is_dir():
        raise ValueError(f"'{path}' does not contain a 'context/changes' directory")
    return path


def load_tracked_projects() -> list[TrackedProject]:
    if not DATA_FILE.is_file():
        return []
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    entries = []
    for item in raw:
        if isinstance(item, str):
            entries.append(TrackedProject(path=Path(item), active=True))
        else:
            entries.append(TrackedProject(path=Path(item["path"]), active=item["active"]))
    return entries


def save_tracked_projects(entries: list[TrackedProject]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(
            [{"path": str(e.path), "active": e.active} for e in entries], indent=2
        ),
        encoding="utf-8",
    )


def add_tracked_project(path: Path) -> Path:
    validated = validate_project_path(path)
    resolved = validated.resolve()
    tracked = load_tracked_projects()
    for existing in tracked:
        if existing.path.resolve().as_posix().lower() == resolved.as_posix().lower():
            raise ValueError(f"'{path}' is already tracked")
    tracked.append(TrackedProject(path=resolved, active=True))
    save_tracked_projects(tracked)
    return resolved


def remove_tracked_project(path: Path) -> None:
    resolved = path.resolve()
    tracked = load_tracked_projects()
    remaining = [
        entry
        for entry in tracked
        if entry.path.resolve().as_posix().lower() != resolved.as_posix().lower()
    ]
    if len(remaining) == len(tracked):
        raise ValueError(f"'{path}' is not tracked")
    save_tracked_projects(remaining)


def set_project_active(path: Path, active: bool) -> None:
    resolved = path.resolve()
    tracked = load_tracked_projects()
    for entry in tracked:
        if entry.path.resolve().as_posix().lower() == resolved.as_posix().lower():
            entry.active = active
            save_tracked_projects(tracked)
            return
    raise ValueError(f"'{path}' is not tracked")
