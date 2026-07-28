from pathlib import Path

from app.roadmap_correlation import get_roadmap_correlations


def _write_roadmap(context_dir: Path, content: str) -> None:
    foundation_dir = context_dir / "foundation"
    foundation_dir.mkdir(parents=True, exist_ok=True)
    (foundation_dir / "roadmap.md").write_text(content, encoding="utf-8")


def test_no_roadmap_md_returns_empty_dict(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()

    assert get_roadmap_correlations(context_dir) == {}


def test_no_at_a_glance_heading_returns_empty_dict(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    _write_roadmap(context_dir, "# Roadmap\n\nNo table heading here.\n")

    assert get_roadmap_correlations(context_dir) == {}


def test_heading_with_no_table_rows_returns_empty_dict(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    _write_roadmap(
        context_dir,
        """# Roadmap

## At a glance

No table follows, just prose.
""",
    )

    assert get_roadmap_correlations(context_dir) == {}


def test_valid_multi_row_table_parsed_and_keyed_by_change_id(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    _write_roadmap(
        context_dir,
        """# Roadmap

## At a glance

| ID   | Change ID                    | Outcome (user can ...)                                              | Prerequisites | PRD refs             | Status   |
| ---- | ----------------------------- | ------------------------------------------------------------------ | -------------- | --------------------- | -------- |
| F-01 | minimal-web-app-scaffold      | (foundation) a running FastAPI app serves a browser-viewable page  | -              | -                     | done     |
| S-01 | project-change-status-view    | add a project path and see its changes with status                | F-01            | US-01, FR-001, FR-003 | done |
| S-02 | project-list-aggregate-status | see all added projects with aggregated new/in-progress/done counts | S-01            | US-01, FR-002         | done     |
| S-03 | change-phase-progress         | see phase progress within each change (e.g. "Phase 3: 4/5")        | S-01            | US-01, FR-004         | proposed |
| S-04 | roadmap-correlation-view      | see which roadmap items each change addresses                     | S-01            | US-01, FR-005         | proposed |
| S-05 | remove-project                | remove a project from the app                                     | S-01            | FR-009                | done     |
| S-06 | manual-single-project-sync    | manually sync a single project to refresh its status               | S-01            | FR-006                | done |
| S-07 | sync-all-projects             | sync all added projects at once                                    | S-02, S-06      | FR-007                | proposed |
| S-08 | configure-autosync-interval   | configure an autosync interval for automatic refreshes             | S-07            | FR-008                | done     |

## Streams

Not part of the table.
""",
    )

    result = get_roadmap_correlations(context_dir)

    assert len(result) == 9
    assert result["roadmap-correlation-view"].roadmap_id == "S-04"
    assert result["roadmap-correlation-view"].outcome == "see which roadmap items each change addresses"
    assert result["roadmap-correlation-view"].prerequisites == ["S-01"]
    assert result["roadmap-correlation-view"].status == "proposed"
    assert result["roadmap-correlation-view"].order == 4
    assert result["configure-autosync-interval"].roadmap_id == "S-08"
    # keyed by change_id (index 1), not roadmap id (index 0)
    assert "S-04" not in result


def test_malformed_row_with_too_few_cells_is_skipped(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    _write_roadmap(
        context_dir,
        """# Roadmap

## At a glance

| ID   | Change ID   | Outcome (user can ...) |
| ---- | ----------- | ----------------------- |
| only-one-cell |
| S-01 | some-change | do the thing            |
""",
    )

    result = get_roadmap_correlations(context_dir)

    assert result == {}
