# See Phase Progress Within a Change — Implementation Plan

## Overview

Extend the dashboard's per-change display to show phase/task progress (e.g. "Phase 3: 4/5") parsed from each change's `plan.md`, alongside the status already shown from `change.md`. This is roadmap item **S-03** (`change-phase-progress`), building on S-01's per-change-folder parsing pattern.

## Current State Analysis

- [app/changes.py](../../../app/changes.py) parses `change.md` per change folder in `list_changes()`, isolating per-folder failures so one bad file never breaks the whole project response — the established pattern this change extends to a second file type.
- [app/api.py](../../../app/api.py)'s `ProjectResponse` model wraps `changes: list[ChangeSummary]`; FastAPI's `response_model` serializes whatever fields `ChangeSummary` declares, so no `api.py` code change is needed to expose a new field — only `ChangeSummary` itself needs to grow.
- [dist/app.js](../../../dist/app.js) renders each change as a single `<li>` with `textContent` built from a template literal, in two places: `renderProjectSection()` (initial load) and `syncProject()` (post-refresh re-render). Both must be updated in lockstep — this duplication already exists for `title`/`status`/`updated` and is not being refactored away here.
- The `## Progress` section format inside `plan.md` is precisely specified in [progress-format.md](../../../.claude/skills/10x-plan/references/progress-format.md): one `### Phase N: <name>` block per phase, each with `#### Automated`/`#### Manual` subsections (either may be omitted), steps as `- [ ] N.M <title>` or `- [x] N.M <title> — <sha>`.
- Real in-repo data confirms the contract holds in practice but with real-world messiness worth parsing defensively: `context/archive/2026-07-23-remove-project/plan.md` has 3 phases with mixed completion and a SHA-suffix comment `— b85acc8 (mixed with unrelated commit; content verified)`; `context/changes/manual-single-project-sync/plan.md` has a single phase with `#### Automated` fully done and `#### Manual` untouched.
- Not every change has a `plan.md` yet — a change at `status: new`/`preparing` has only `change.md`. `list_changes()` already tolerates a change folder with no `change.md` at all (skipped entirely), establishing that "file doesn't exist yet" is a normal, expected state in this codebase, not an error.

## Desired End State

Every change row in the dashboard that has a `plan.md` with a populated `## Progress` section shows its current phase and task ratio inline, e.g. `Some Change [implementing] — updated 2026-07-23 — Phase 2: 2/4`. Changes with no `plan.md`, no `## Progress` section, or an unparseable one show no phase-progress suffix at all — same as today, no error surfaced. A change with every step checked off shows its last phase at full ratio (e.g. `Phase 3: 5/5`).

**Verification**: point the app at this repo's own `context/` (it has real examples of every state: no plan, single-phase partial, multi-phase partial, and — once `manual-single-project-sync` finishes — fully done), confirm each change row shows the expected phase text or lack thereof.

### Key Discoveries:

- `progress-format.md`'s own "Parsing contract for tooling" section already defines "current phase" as *"phase containing the first `- [ ]`, or last phase if all done"* — this plan does not invent new semantics, it implements an existing spec.
- `ChangeSummary` in `app/changes.py:9-14` is a flat Pydantic model with no nested structure yet; adding a nested `PhaseProgress` field is a small, additive change with no migration concerns since there's no persisted schema (data is always re-read from disk).

## What We're NOT Doing

- No roadmap correlation (that's S-04, `roadmap-correlation-view`).
- No surfacing of *which specific step* is next or its title — only the phase number and the done/total ratio, matching the PRD's literal "Phase 3: 4/5" example.
- No separate error field for malformed/missing `plan.md` or `## Progress` sections — per user decision, these all collapse to "no phase progress shown," the same as a change that was never planned.
- No distinction between Automated and Manual step counts in the displayed ratio — they're combined, per user decision.
- No caching of parsed plan data — `plan_progress.py` re-parses `plan.md` from disk on every call, consistent with `list_changes()`'s existing always-fresh-read design (`GET /api/projects` already has no caching layer to plug into).
- No changes to `app/api.py` — the new field flows through the existing `response_model` automatically.

## Implementation Approach

Add a new, standalone parsing module (`app/plan_progress.py`) mirroring `app/changes.py`'s shape: one pure function taking a `Path`, returning a small Pydantic model or `None`, with all failure modes collapsing to `None` rather than raising. Wire its result into `ChangeSummary` from within `list_changes()`'s existing per-folder loop (the loop already has the change folder `Path` in scope). No `api.py` changes. Frontend gets one template-literal edit in each of the two existing render call sites.

## Critical Implementation Details

**Current-phase selection algorithm**: iterate phase blocks in document order (as they appear in `## Progress`, which is always phase-number order per the format contract); the current phase is the *first* block containing at least one `- [ ]` line. If every phase block has zero unchecked lines (all done), the current phase is the *last* block instead. If a block has zero bullets at all (shouldn't happen per contract, but parse defensively), skip it when selecting — don't let an empty phase falsely become "current." If the whole `## Progress` section has zero bullets across every phase, return `None` (nothing to report) rather than a `0/0` phase.

**Combined counting, subsection-agnostic**: `#### Automated` and `#### Manual` headings are not used for counting — every `- [ ]`/`- [x]` line within a phase block (regardless of which subsection it falls under, or whether both are present) counts toward that phase's `done`/`total`. The bullet regex is subsection-independent: `^- \[([ xX])\]` per line, scoped to lines between one `### Phase` heading and the next (or end of file for the last phase).

## Phase 1: `plan.md` parsing module

### Overview

A standalone, pure-function module that parses a change folder's `plan.md` into a phase-progress result, tolerating every documented and observed edge case (no file, no section, empty phases, trailing SHA-comment text) by returning `None` rather than raising.

### Changes Required:

#### 1. `app/plan_progress.py` (new)

**Intent**: Parse the `## Progress` section of a change's `plan.md` into the current phase's done/total step counts, per the algorithm in Critical Implementation Details above.

**Contract**: Exposes `get_phase_progress(change_dir: Path) -> PhaseProgress | None` and a `PhaseProgress` Pydantic model with fields `phase_number: int`, `done: int`, `total: int`. Returns `None` when: `change_dir / "plan.md"` doesn't exist; the file has no `## Progress` heading; the section has no phase blocks or no bullets in any block; or any exception occurs while reading/parsing (caught and swallowed — this function never raises). Phase blocks are located via `^### Phase (\d+):`; bullets via `^- \[([ xX])\]` scoped per block.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_plan_progress.py -v` passes — covers: no `plan.md`, no `## Progress` section, single-phase partial (mirrors `manual-single-project-sync/plan.md`'s real shape: automated done, manual pending), multi-phase with an earlier fully-done phase (mirrors the archived `remove-project/plan.md`'s real shape — phase 1 done, phase 2 partial is "current"), all-phases-done (last phase reported), a phase with only `#### Manual` (no `#### Automated` subsection) still counts correctly, and a SHA-suffix trailing comment (`— abc1234 (some note)`) doesn't break the checkbox match.

---

## Phase 2: Wire into `ChangeSummary` and the API response

### Overview

Attach the Phase 1 parser's result to each change as it's built in `changes.py`'s existing loop, so it flows through `GET /api/projects`, `POST /api/projects`, and `DELETE /api/projects`'s response automatically via the existing `response_model`.

### Changes Required:

#### 1. `app/changes.py`

**Intent**: Add the new field to `ChangeSummary` and populate it during `list_changes()`'s existing per-folder iteration, using the folder `Path` already in scope there.

**Contract**: `ChangeSummary` gains `phase_progress: PhaseProgress | None = None` (imported from `app.plan_progress`). In `list_changes()`'s loop, after building each `ChangeSummary` via `_parse_change_md`, set `summary.phase_progress = get_phase_progress(entry)` before appending — independent of whether `change.md` itself parsed cleanly, since the two files are unrelated failure domains.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_changes.py -v` passes — extended with cases confirming `phase_progress` is populated when a fixture change folder has a matching `plan.md`, and is `None` when it doesn't
- [ ] `uv run pytest tests/test_api.py -v` passes — extended with a fixture project whose change folder includes a `plan.md`, asserting `GET /api/projects` and `POST /api/projects` responses include the expected `phase_progress` object

---

## Phase 3: Frontend rendering

### Overview

Append the phase-progress text inline to the existing per-change line, in both places it's rendered.

### Changes Required:

#### 1. `dist/app.js`

**Intent**: Extend the per-change `<li>` text to include `— Phase N: X/Y` when `change.phase_progress` is present, leaving the line unchanged when it's `null`.

**Contract**: Both the initial-render loop in `renderProjectSection()` and the post-refresh loop in `syncProject()` get the same conditional suffix appended to their existing `item.textContent` template literal, keeping the two render paths in sync as they already must be for `title`/`status`/`updated`.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run python -c "import app.main"` succeeds

#### Manual Verification:

- [ ] Browser: point the app at this repo's own path; `manual-single-project-sync` (single phase, automated done / manual pending) shows its correct partial ratio
- [ ] Browser: a change with multiple phases where an earlier one is fully done shows the correct later phase as current (not phase 1)
- [ ] Browser: a change with no `plan.md` (or status still `new`) shows no phase-progress text and the row looks unchanged from today
- [ ] Browser: click "Refresh" on a project and confirm the phase-progress text updates/persists correctly via `syncProject()`'s re-render path, not just on initial load

---

## Testing Strategy

### Unit Tests:

- `plan_progress.py`'s edge cases in isolation (Phase 1), independent of any HTTP or file-tree fixture beyond a `tmp_path`-written `plan.md`.

### Integration Tests:

- `test_changes.py` and `test_api.py` extensions confirming the field flows end-to-end from a fixture `plan.md` through to the JSON response shape.

### Manual Testing Steps:

1. Run the app against this repo's own `context/` directory (has real `plan.md` files in every state this feature needs to handle).
2. Confirm `manual-single-project-sync`'s row shows its real partial ratio.
3. Confirm a change with no `plan.md` shows nothing extra.
4. Refresh and confirm the phase text updates via the sync path, not just initial load.

## Performance Considerations

None beyond what already exists — `plan.md` files are small (a few KB), parsed with simple line-based regex matching, and read fresh on every request just like `change.md` already is.

## Migration Notes

None — no persisted schema, no data migration; every read is fresh from disk.

## References

- Related roadmap item: `context/foundation/roadmap.md` (S-03, `change-phase-progress`)
- Progress section contract: `.claude/skills/10x-plan/references/progress-format.md`
- Established per-file-isolation pattern: `app/changes.py:34-57` (`_parse_change_md`)
- Real multi-phase example (mixed completion): `context/archive/2026-07-23-remove-project/plan.md`
- Real single-phase example (partial): `context/changes/manual-single-project-sync/plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: `plan.md` parsing module

#### Automated

- [x] 1.1 `uv run pytest tests/test_plan_progress.py -v` passes — 6eeea0d

### Phase 2: Wire into `ChangeSummary` and the API response

#### Automated

- [ ] 2.1 `uv run pytest tests/test_changes.py -v` passes
- [ ] 2.2 `uv run pytest tests/test_api.py -v` passes

### Phase 3: Frontend rendering

#### Automated

- [ ] 3.1 `uv run python -c "import app.main"` succeeds

#### Manual

- [ ] 3.2 Browser: `manual-single-project-sync` shows its correct partial ratio
- [ ] 3.3 Browser: multi-phase change with an earlier fully-done phase shows the correct later phase as current
- [ ] 3.4 Browser: a change with no `plan.md` shows no phase-progress text
- [ ] 3.5 Browser: Refresh updates the phase-progress text via the sync re-render path
