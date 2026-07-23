from pathlib import Path

from app.plan_progress import get_phase_progress


def _write_plan(change_dir: Path, content: str) -> None:
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "plan.md").write_text(content, encoding="utf-8")


def test_no_plan_md_returns_none(tmp_path: Path) -> None:
    change_dir = tmp_path / "some-change"
    change_dir.mkdir()

    assert get_phase_progress(change_dir) is None


def test_no_progress_section_returns_none(tmp_path: Path) -> None:
    change_dir = tmp_path / "some-change"
    _write_plan(change_dir, "# Plan\n\nNo progress section here.\n")

    assert get_phase_progress(change_dir) is None


def test_single_phase_partial_automated_done_manual_pending(tmp_path: Path) -> None:
    change_dir = tmp_path / "manual-single-project-sync"
    _write_plan(
        change_dir,
        """# Plan

## Progress

> Convention: `- [ ]` pending, `- [x]` done.

### Phase 1: Frontend UI — Refresh Button & Loading State

#### Automated

- [x] 1.1 `uv run python -c "import app.main"` succeeds — 06c6411
- [x] 1.2 `curl http://127.0.0.1:8000/` returns HTTP 200 — 06c6411

#### Manual

- [ ] 1.3 Browser: Click "Refresh", spinner appears, data updates
- [ ] 1.4 Browser: External `change.md` edit appears after refresh
- [ ] 1.5 Browser: Concurrent syncs work (multiple projects refresh in parallel)
- [ ] 1.6 Browser: Sync error shows inline without removing project
""",
    )

    result = get_phase_progress(change_dir)

    assert result is not None
    assert result.phase_number == 1
    assert result.done == 2
    assert result.total == 6


def test_multi_phase_earlier_phase_fully_done_is_not_current(tmp_path: Path) -> None:
    change_dir = tmp_path / "remove-project"
    _write_plan(
        change_dir,
        """# Plan

## Progress

> Convention: `- [ ]` pending, `- [x]` done.

### Phase 1: Persistence layer

#### Automated

- [x] 1.1 `uv run pytest tests/test_projects.py -v` passes — b85acc8 (mixed with unrelated commit; content verified)

### Phase 2: API layer

#### Automated

- [x] 2.1 `uv run pytest tests/test_api.py -v` passes — 6666af1
- [x] 2.2 `uv run python -c "import app.main"` succeeds — 6666af1

#### Manual

- [ ] 2.3 `/docs` shows `DELETE /api/projects` with correct schemas
- [ ] 2.4 `POST` then `DELETE` via `/docs`, confirm `GET` no longer includes it

### Phase 3: Frontend UI

#### Automated

- [x] 3.1 `uv run python -c "import app.main"` succeeds — a211f07
""",
    )

    result = get_phase_progress(change_dir)

    assert result is not None
    assert result.phase_number == 2
    assert result.done == 2
    assert result.total == 4


def test_all_phases_done_reports_last_phase(tmp_path: Path) -> None:
    change_dir = tmp_path / "all-done"
    _write_plan(
        change_dir,
        """# Plan

## Progress

### Phase 1: Setup

#### Automated

- [x] 1.1 First step — abc1234

### Phase 2: Wrap up

#### Automated

- [x] 2.1 Second step — def5678
- [x] 2.2 Third step — def5678
""",
    )

    result = get_phase_progress(change_dir)

    assert result is not None
    assert result.phase_number == 2
    assert result.done == 2
    assert result.total == 2


def test_manual_only_phase_counts_correctly(tmp_path: Path) -> None:
    change_dir = tmp_path / "manual-only"
    _write_plan(
        change_dir,
        """# Plan

## Progress

### Phase 1: Review

#### Manual

- [x] 1.1 Eyeball the output — abc1234
- [ ] 1.2 Confirm with stakeholder
""",
    )

    result = get_phase_progress(change_dir)

    assert result is not None
    assert result.phase_number == 1
    assert result.done == 1
    assert result.total == 2


def test_sha_suffix_with_trailing_note_does_not_break_match(tmp_path: Path) -> None:
    change_dir = tmp_path / "sha-note"
    _write_plan(
        change_dir,
        """# Plan

## Progress

### Phase 1: Only phase

#### Automated

- [x] 1.1 Some step — abc1234 (mixed with unrelated commit; content verified)
- [ ] 1.2 Another step
""",
    )

    result = get_phase_progress(change_dir)

    assert result is not None
    assert result.phase_number == 1
    assert result.done == 1
    assert result.total == 2


def test_no_bullets_in_any_phase_returns_none(tmp_path: Path) -> None:
    change_dir = tmp_path / "empty-phase"
    _write_plan(
        change_dir,
        """# Plan

## Progress

### Phase 1: Nothing here yet
""",
    )

    assert get_phase_progress(change_dir) is None
