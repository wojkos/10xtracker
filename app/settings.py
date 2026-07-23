import json
from pathlib import Path

DATA_FILE = Path("data/settings.json")

DEFAULT_INTERVAL_MINUTES = 5
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 1440


def load_autosync_settings() -> tuple[bool, int]:
    if not DATA_FILE.is_file():
        return False, DEFAULT_INTERVAL_MINUTES
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return raw["enabled"], raw["interval_minutes"]


def save_autosync_settings(enabled: bool, interval_minutes: int) -> None:
    if not (MIN_INTERVAL_MINUTES <= interval_minutes <= MAX_INTERVAL_MINUTES):
        raise ValueError(
            f"interval_minutes must be between {MIN_INTERVAL_MINUTES} and "
            f"{MAX_INTERVAL_MINUTES}"
        )
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps({"enabled": enabled, "interval_minutes": interval_minutes}, indent=2),
        encoding="utf-8",
    )
