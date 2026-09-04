<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Next Action Dashboard Panel Implementation Plan

- **Plan**: context/changes/next-action-dashboard/plan.md
- **Scope**: Phase 3 of 3 (full plan review)
- **Date**: 2026-09-04
- **Verdict**: APPROVED
- **Findings**: 0 critical, 2 warnings, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — No per-project failure isolation in the recommendation loop

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/workflow_recommendations.py:134-199 (`get_next_10x_action`)
- **Detail**: The per-project loop in `get_next_10x_action()` has no try/except around `_recommend_for_active_change`/`_eligible_roadmap_change`, unlike the existing isolation pattern in `app/changes.py` where a per-change parsing failure is captured into a `ChangeSummary.error` field so one bad record can't break the rest. Lower-level helpers (`get_roadmap_correlations`, `get_phase_progress`) already catch `OSError`, so this is mostly mitigated today, but any other unexpected exception in one project's recommendation logic would 500 the entire `/api/recommendations` response for every tracked project instead of just the offending one.
- **Fix**: Wrap the per-project recommendation call in try/except and degrade to a `_blocked(...)` entry on failure, mirroring the per-change error-isolation pattern already used elsewhere in this codebase.
- **Decision**: FIXED — extracted `_recommend_for_project()` and wrapped its call in `get_next_10x_action()`'s loop in try/except, degrading to `_blocked(...)` on failure.

### F2 — Unplanned test added alongside the recommendations endpoint

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: tests/test_api.py (`test_get_orders_projects_by_most_recently_updated_change`), added in commit 92226e1
- **Detail**: Phase 1's commit added a test for `/api/projects` ordering behavior that is unrelated to the plan's Phase 1 contract (which only calls for recommendations-endpoint coverage). The test itself is valid, passing coverage of pre-existing behavior — not a functional defect, just untracked scope in this commit.
- **Fix**: No functional change needed; leave the test in place as incidental coverage, or move it to a separate commit/note in the plan next time similar incidental coverage is added.
- **Decision**: ACCEPTED — benign, valid coverage; left as-is.

### F3 — Near-duplicate test fixture helper

- **Severity**: OBSERVATION
- **Dimension**: Pattern Consistency
- **Location**: tests/test_api.py (`_make_fixture_project_with_update_date`)
- **Detail**: This helper is a near-duplicate of the existing `_make_fixture_project`/`_make_fixture_project_with_plan` helpers in the same file, parametrized only by date. Minor duplication, not worth blocking on.
- **Fix**: Optional future cleanup — fold the `updated` date into the existing fixture helpers' signature if a third variant appears.
- **Decision**: FIXED — added optional `name`/`updated` kwargs to `_make_fixture_project`, removed the duplicate helper, updated its one caller.
