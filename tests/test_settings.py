from pathlib import Path

import pytest

from app import settings


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DATA_FILE", tmp_path / "data" / "settings.json")


def test_defaults_when_no_file_exists() -> None:
    enabled, interval_minutes = settings.load_autosync_settings()

    assert enabled is False
    assert interval_minutes == settings.DEFAULT_INTERVAL_MINUTES


def test_save_then_load_round_trip() -> None:
    settings.save_autosync_settings(True, 10)

    enabled, interval_minutes = settings.load_autosync_settings()

    assert enabled is True
    assert interval_minutes == 10


def test_interval_below_minimum_rejected() -> None:
    with pytest.raises(ValueError):
        settings.save_autosync_settings(True, settings.MIN_INTERVAL_MINUTES - 1)


def test_interval_above_maximum_rejected() -> None:
    with pytest.raises(ValueError):
        settings.save_autosync_settings(True, settings.MAX_INTERVAL_MINUTES + 1)
