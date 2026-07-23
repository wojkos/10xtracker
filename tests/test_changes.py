from pathlib import Path

from app.changes import list_changes


def _write_change_md(changes_dir: Path, change_id: str, content: str) -> None:
    folder = changes_dir / change_id
    folder.mkdir(parents=True)
    (folder / "change.md").write_text(content, encoding="utf-8")


def test_valid_change_md(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    changes_dir = context_dir / "changes"
    _write_change_md(
        changes_dir,
        "some-change",
        """---
change_id: some-change
title: Some Change
status: implementing
created: 2026-07-23
updated: 2026-07-23
archived_at: null
---
""",
    )

    result = list_changes(context_dir)

    assert len(result) == 1
    summary = result[0]
    assert summary.change_id == "some-change"
    assert summary.title == "Some Change"
    assert summary.status == "implementing"
    assert summary.updated == "2026-07-23"
    assert summary.error is None


def test_malformed_yaml_is_flagged(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    changes_dir = context_dir / "changes"
    _write_change_md(
        changes_dir,
        "broken-yaml",
        """---
change_id: broken-yaml
title: [unterminated
status: new
---
""",
    )

    result = list_changes(context_dir)

    assert len(result) == 1
    assert result[0].change_id == "broken-yaml"
    assert result[0].error is not None


def test_missing_required_field_is_flagged(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    changes_dir = context_dir / "changes"
    _write_change_md(
        changes_dir,
        "missing-status",
        """---
change_id: missing-status
title: Missing Status
updated: 2026-07-23
---
""",
    )

    result = list_changes(context_dir)

    assert len(result) == 1
    assert result[0].change_id == "missing-status"
    assert result[0].error is not None
    assert "status" in result[0].error


def test_folder_without_change_md_is_skipped(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    changes_dir = context_dir / "changes"
    no_change_md = changes_dir / "bootstrap-verification"
    no_change_md.mkdir(parents=True)
    (no_change_md / "verification.md").write_text("no change.md here", encoding="utf-8")

    result = list_changes(context_dir)

    assert result == []


def test_one_bad_folder_does_not_break_others(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    changes_dir = context_dir / "changes"
    _write_change_md(
        changes_dir,
        "broken",
        """---
change_id: broken
title: [unterminated
---
""",
    )
    _write_change_md(
        changes_dir,
        "good",
        """---
change_id: good
title: Good Change
status: new
updated: 2026-07-23
---
""",
    )

    result = list_changes(context_dir)

    by_id = {summary.change_id: summary for summary in result}
    assert len(result) == 2
    assert by_id["broken"].error is not None
    assert by_id["good"].error is None
    assert by_id["good"].status == "new"
