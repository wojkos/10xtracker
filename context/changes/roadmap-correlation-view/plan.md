# See Roadmap Correlation Per Change — Implementation Plan

## Overview

Extend the dashboard's per-change display to show which roadmap item a change addresses (e.g. `S-04: see which roadmap items each change addresses`), parsed from the project's `foundation/roadmap.md`. This is roadmap item **S-04** (`roadmap-correlation-view`), building on S-01's per-change-folder parsing pattern and following the same shape S-03 (`change-phase-progress`) just shipped.

## Current State Analysis

- [app/changes.py](../../../app/changes.py) parses `change.md` per change folder in `list_changes()`, then separately attaches `plan.md`-derived phase progress per folder via `get_phase_progress()`. Roadmap correlation is project-level data (one `roadmap.md`, many changes), not per-folder data, so it must be parsed once per `list_changes()` call rather than once per change folder.
- [app/plan_progress.py](../../../app/plan_progress.py) is the direct precedent for this change's shape: a standalone module exposing one pure function that takes a `Path`, returns a small Pydantic model (or absence value) for every documented and observed edge case, and never raises.
- [dist/app.js](../../../dist/app.js) has a `formatPhaseProgress()` helper whose output is appended to the per-change `<li>` text in two places: `renderProjectSection()` (initial load) and `syncProject()` (post-refresh re-render). This change adds a sibling `formatRoadmapCorrelation()` helper appended the same way, in both places.
- `foundation/roadmap.md`'s `## At a glance` table is a schema-enforced contract, not ad-hoc formatting: `.claude/skills/10x-roadmap/SKILL.md:466-470` fixes its six columns (`ID`, `Change ID`, `Outcome (user can …)`, `Prerequisites`, `PRD refs`, `Status`) in that order, and `SKILL.md:595` (Change ID integrity) guarantees every `Change ID` in the document is unique — so a lookup by `change_id` never needs to handle multiple matches, only zero or one.
- Real in-repo data (this project's own `context/foundation/roadmap.md`) confirms the contract holds in practice and gives realistic test/manual-verification fixtures: 9 rows (`F-01` through `S-08`), all currently matched 1:1 to real change folders in this repo.
- Not every project this app points at is guaranteed to have a `foundation/roadmap.md` (a project may not have run `/10x-roadmap` yet), and not every change's `change_id` is guaranteed to appear in that table (ad-hoc changes created without a roadmap slice). Both are normal, expected absences — not errors.

## Desired End State

Every change row in the dashboard whose `change_id` has a matching entry in its project's `foundation/roadmap.md` `## At a glance` table shows the roadmap ID and outcome text inline, e.g. `Some Change [implementing] — updated 2026-07-23 — Phase 2: 2/4 — S-04: see which roadmap items each change addresses`. Changes with no match (no `roadmap.md`, no `## At a glance` table, or `change_id` absent from it) show no roadmap-correlation suffix at all — same as today, no error surfaced.

**Verification**: point the app at this repo's own `context/` (its `roadmap.md` has 9 real rows covering every current change folder), confirm each change row shows its correct roadmap ID + outcome text.

### Key Discoveries:

- The table's column order and header text are fixed by the roadmap-generation skill's own validation rules, so parsing by fixed column index (0 = ID, 1 = Change ID, 2 = Outcome) is safe — no header-name matching needed.
- `ChangeSummary` in `app/changes.py:11-17` already holds one optional nested-model field (`phase_progress`) added by S-03; adding a second sibling optional field (`roadmap_correlation`) is the same small, additive, no-migration-concern change repeated once.

## What We're NOT Doing

- No display of `Prerequisites`, `PRD refs`, or `Status` columns from the roadmap table — only `ID` and `Outcome`, per user decision (keeps the inline line readable, matches what a user actually needs to answer "which roadmap item does this address").
- No truncation of the outcome text — displayed in full, consistent with how `title` and other fields are already shown untruncated on the same line.
- No handling of a change matching more than one roadmap row — the roadmap-generation skill's own integrity rule guarantees uniqueness, so this case cannot occur for a validly-generated `roadmap.md`; a malformed document with a duplicate is resolved by "last row wins" as a natural consequence of building the lookup dict in document order, not a designed behavior.
- No separate error field or user-facing message for a missing/malformed `roadmap.md` or `## At a glance` table — collapses to "no roadmap correlation shown," same convention `plan_progress.py` established for missing/malformed `plan.md`.
- No caching of the parsed roadmap table — re-parsed from disk on every `list_changes()` call, consistent with the existing always-fresh-read design.
- No changes to `app/api.py` — the new field flows through the existing `response_model` automatically, exactly as `phase_progress` did.

## Implementation Approach

Add a new, standalone parsing module (`app/roadmap_correlation.py`) mirroring `app/plan_progress.py`'s shape: one pure function taking the project's `context_dir: Path`, returning a `dict[str, RoadmapCorrelation]` keyed by `change_id` (empty dict on any failure, never raises). Unlike `plan_progress`, this is called **once** per `list_changes()` invocation (not once per change folder), since the source file is project-level; the resulting dict is then looked up per change inside the existing per-folder loop. Frontend gets one new helper function and one template-literal edit in each of the two existing render call sites.

## Critical Implementation Details

**Table parsing boundary**: the `## At a glance` table's rows are contiguous lines starting with `|`, immediately following the `## At a glance` heading (first the header row, then the separator row of dashes, then data rows). Parsing stops at the first line encountered that does not start with `|` after table rows have begun — this naturally ends the table exactly where the section's prose or the next `##` heading begins, without needing to search for the next heading explicitly.

**Column extraction**: split each data row on `|`, strip the empty leading/trailing cells produced by the row's own leading/trailing `|`, then strip whitespace from each remaining cell. Index 0 is the roadmap ID (e.g. `S-04`), index 1 is the `change_id` used as the dict key, index 2 is the outcome text. A row that doesn't split into at least 3 cells (malformed) is skipped rather than raising — defensive parsing consistent with `plan_progress.py`'s per-line tolerance.

## Phase 1: `roadmap.md` correlation parsing module

### Overview

A standalone, pure-function module that parses a project's `foundation/roadmap.md` `## At a glance` table into a `change_id → RoadmapCorrelation` lookup, tolerating every documented and observed edge case (no file, no heading, no table rows, malformed rows) by returning an empty dict rather than raising.

### Changes Required:

#### 1. `app/roadmap_correlation.py` (new)

**Intent**: Parse the `## At a glance` table of a project's `roadmap.md` into a lookup from `change_id` to that change's roadmap ID and outcome text, per the parsing boundary and column-extraction rules in Critical Implementation Details above.

**Contract**: Exposes `get_roadmap_correlations(context_dir: Path) -> dict[str, RoadmapCorrelation]` and a `RoadmapCorrelation` Pydantic model with fields `roadmap_id: str`, `outcome: str`. Returns `{}` when: `context_dir / "foundation" / "roadmap.md"` doesn't exist; the file has no `## At a glance` heading; the heading is followed by no table rows; or any exception occurs while reading/parsing (caught and swallowed — this function never raises). Table rows are located as contiguous `|`-prefixed lines immediately after the heading, with the first row (header) and second row (dash separator) skipped and the rest treated as data.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_roadmap_correlation.py -v` passes — covers: no `roadmap.md`, no `## At a glance` heading, heading with no table rows, a valid multi-row table (mirrors this repo's own real `roadmap.md` shape — 9 rows including a `Change ID` value not exercised elsewhere), a malformed row with too few cells skipped without breaking other rows, and confirms lookup is keyed by `change_id` (index 1) not roadmap ID (index 0)

---

## Phase 2: Wire into `ChangeSummary` and the API response

### Overview

Attach the Phase 1 parser's result to each change as `list_changes()` builds it, parsing the roadmap table once per call and looking it up per change by `change_id`, so it flows through `GET /api/projects`, `POST /api/projects`, and `DELETE /api/projects`'s response automatically via the existing `response_model`.

### Changes Required:

#### 1. `app/changes.py`

**Intent**: Add the new field to `ChangeSummary` and populate it during `list_changes()`, parsing the roadmap table once (outside the per-folder loop, since it's project-level data) and looking up each change's entry by its own `change_id` inside the existing loop.

**Contract**: `ChangeSummary` gains `roadmap_correlation: RoadmapCorrelation | None = None` (imported from `app.roadmap_correlation`). In `list_changes()`, call `get_roadmap_correlations(context_dir)` once before the per-folder loop begins, then inside the loop set `summary.roadmap_correlation = correlations.get(summary.change_id)` — using `summary.change_id` (always set, even on a `change.md` parse error, since it falls back to the folder name) rather than the folder name directly, so behavior is identical either way but reads from the single source of truth already on the summary.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_changes.py -v` passes — extended with cases confirming `roadmap_correlation` is populated when a fixture project's `roadmap.md` has a matching `Change ID` row, and is `None` when it doesn't (including when `roadmap.md` itself is absent)
- [ ] `uv run pytest tests/test_api.py -v` passes — extended with a fixture project whose `context/foundation/roadmap.md` includes a matching row, asserting `GET /api/projects` and `POST /api/projects` responses include the expected `roadmap_correlation` object

---

## Phase 3: Frontend rendering

### Overview

Append the roadmap-correlation text inline to the existing per-change line, in both places it's rendered, mirroring how `formatPhaseProgress()` was added for S-03.

### Changes Required:

#### 1. `dist/app.js`

**Intent**: Add a `formatRoadmapCorrelation()` helper and extend the per-change `<li>` text to include `— <roadmap_id>: <outcome>` when `change.roadmap_correlation` is present, leaving the line unchanged when it's `null`.

**Contract**: Both the initial-render loop in `renderProjectSection()` and the post-refresh loop in `syncProject()` get the same conditional suffix appended to their existing `item.textContent` template literal (after the existing `formatPhaseProgress()` suffix), keeping the two render paths in sync as they already must be for `title`/`status`/`updated`/`phase_progress`.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run python -c "import app.main"` succeeds

#### Manual Verification:

- [ ] Browser: point the app at this repo's own path; every change row shows its correct `<roadmap_id>: <outcome>` suffix matching `context/foundation/roadmap.md`'s `## At a glance` table
- [ ] Browser: click "Refresh" on a project and confirm the roadmap-correlation text persists correctly via `syncProject()`'s re-render path, not just on initial load
- [ ] Browser: a change row appears alongside its phase-progress suffix without visual crowding or truncation issues on a typical browser window width

---

## Testing Strategy

### Unit Tests:

- `roadmap_correlation.py`'s edge cases in isolation (Phase 1), independent of any HTTP or file-tree fixture beyond a `tmp_path`-written `roadmap.md`.

### Integration Tests:

- `test_changes.py` and `test_api.py` extensions confirming the field flows end-to-end from a fixture `roadmap.md` through to the JSON response shape.

### Manual Testing Steps:

1. Run the app against this repo's own `context/` directory (its `roadmap.md` has real rows for every current change folder).
2. Confirm each change row shows its correct roadmap ID + outcome text.
3. Refresh and confirm the roadmap-correlation text persists via the sync path, not just initial load.

## Performance Considerations

None beyond what already exists — `roadmap.md` files are small (a few KB), parsed with simple line-based string splitting, and read fresh once per `list_changes()` call rather than once per change folder (an improvement over a naive per-folder re-parse, since the source data is identical for every change in a project).

## Migration Notes

None — no persisted schema, no data migration; every read is fresh from disk.

## References

- Related roadmap item: `context/foundation/roadmap.md` (S-04, `roadmap-correlation-view`)
- Roadmap table contract: `.claude/skills/10x-roadmap/SKILL.md:466-470,590,595`
- Established per-file-isolation pattern: `app/plan_progress.py` (S-03's parsing module)
- Established per-project field wiring: `app/changes.py` (S-03's `phase_progress` wiring in `list_changes()`)
- Established frontend append pattern: `dist/app.js`'s `formatPhaseProgress()` and its two call sites

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: `roadmap.md` correlation parsing module

#### Automated

- [x] 1.1 `uv run pytest tests/test_roadmap_correlation.py -v` passes — 0e4e3e1

### Phase 2: Wire into `ChangeSummary` and the API response

#### Automated

- [x] 2.1 `uv run pytest tests/test_changes.py -v` passes
- [x] 2.2 `uv run pytest tests/test_api.py -v` passes

### Phase 3: Frontend rendering

#### Automated

- [ ] 3.1 `uv run python -c "import app.main"` succeeds

#### Manual

- [ ] 3.2 Browser: every change row shows its correct roadmap ID + outcome text
- [ ] 3.3 Browser: Refresh persists the roadmap-correlation text via the sync re-render path
- [ ] 3.4 Browser: roadmap-correlation text alongside phase-progress reads cleanly without crowding
