import json
from pathlib import Path

DATA_FILE = Path("data/tracked_projects.json")


def validate_project_path(path: Path) -> Path:
    if not (path / "context" / "changes").is_dir():
        raise ValueError(f"'{path}' does not contain a 'context/changes' directory")
    return path


def load_tracked_projects() -> list[Path]:
    if not DATA_FILE.is_file():
        return []
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [Path(p) for p in raw]


def save_tracked_projects(paths: list[Path]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps([str(p) for p in paths], indent=2), encoding="utf-8"
    )


def add_tracked_project(path: Path) -> Path:
    validated = validate_project_path(path)
    resolved = validated.resolve()
    tracked = load_tracked_projects()
    for existing in tracked:
        if existing.resolve().as_posix().lower() == resolved.as_posix().lower():
            raise ValueError(f"'{path}' is already tracked")
    tracked.append(resolved)
    save_tracked_projects(tracked)
    return resolved
