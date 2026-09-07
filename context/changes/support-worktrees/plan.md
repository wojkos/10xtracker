# Worktree-Aware Recommendations Implementation Plan

## Overview

Extend 10xtracker's recommendation engine so it detects git worktrees
belonging to a tracked project, correlates each worktree to the active
change it is processing, and uses that worktree's `change.md` as the
authoritative status for that change. Instead of blocking whenever more
than one change is active, the app now returns one recommendation per
active change — worktree-backed changes get a real, branch-labeled command;
changes with no worktree still get an individual "which one next" prompt.

## Current State Analysis

- [app/changes.py:65](../../../app/changes.py) `list_changes(context_dir)` reads `change.md` from a
  single fixed path with no git or worktree awareness.
- [app/project_status.py:15](../../../app/project_status.py) `get_project_status` calls `list_changes`
  against the tracked project's single main-checkout path only.
- [app/workflow_recommendations.py:174](../../../app/workflow_recommendations.py) `_recommend_for_project`
  returns exactly one `WorkflowRecommendation` per project. When
  `len(active_changes) > 1` it always blocks with
  `"Which change can be worked on next?"`, listing every active `change_id`
  as a candidate (line 200-213).
- [dist/app.js:399-422](../../../dist/app.js) already renders `blocking_question`,
  `candidates`, and `candidate_commands` as a list — the pattern a `branch`
  label slots into.
- [tests/test_api.py:22-41](../../../tests/test_api.py) and
  `tests/test_workflow_recommendations.py` build fixture projects as plain
  directories (`validate_project_path` only checks for a `context/changes`
  folder — it never requires a git repo). None of today's fixtures are git
  repos, which is why worktree detection must fail silently rather than
  raise.

## Desired End State

`GET /api/recommendations` returns one `WorkflowRecommendation` per active
change. When an active change has a linked git worktree (a worktree whose
`context/changes/<id>/` folder exists), that change's status comes from the
worktree's own `change.md`, and the recommendation carries a `branch` field
showing which branch is handling it. The dashboard's next-action panel
renders that as a `(branch)` prefix next to the command. Changes with no
worktree keep today's individually-blocked behavior. Verify by tracking a
project with two active changes, one of them backed by a `git worktree add`
checkout, and confirming `/api/recommendations` returns two entries: one
real command with `branch` set, one blocked entry naming just that change.

### Key Discoveries:

- `git worktree list --porcelain` against this repo returns a
  `worktree <path>` / `HEAD <sha>` / `branch refs/heads/<name>` block per
  worktree, separated by blank lines; a detached worktree replaces the
  `branch` line with `detached`. A worktree can also carry an extra
  `locked <reason>` line (see below) — the parser must skip lines it
  doesn't recognize rather than assume a fixed 3-line block.
- **Live, real-world proof of the correlation strategy**: this repo
  already has a second worktree at `.claude/worktrees/archive-project`
  (branch `worktree-archive-project`), created by Claude Code's own
  worktree tooling and currently `git worktree lock`-ed with a reason
  string naming the Claude session and PID. It contains its own
  `context/changes/archive-project/change.md` (status `planned`). This
  confirms path-match correlation works with zero extra code against a
  real worktree, not just a hypothetical one.
- **Do not assume Claude Code's own worktree-naming convention.**
  `.claude/worktrees/<name>` as a location and `worktree-<name>` as a
  branch name are specific to Claude Code's `EnterWorktree`/`ExitWorktree`
  tooling — not a general git-worktree convention. A worktree created by
  a plain `git worktree add <path> -b <anything>` will not follow this
  naming. The path-match design already avoids depending on it (it only
  checks for `context/changes/<id>/`, never the worktree's path or branch
  name), and Phase 1 must keep it that way rather than special-casing the
  `.claude/worktrees/` layout.
- `list_changes()` is already reusable as-is against any `context/` dir —
  including a worktree's own `context/` — so correlating a worktree to a
  change needs no new frontmatter-parsing code, just a second call to the
  existing function.
- Pydantic is v2.13.4 (`uv.lock`), so attaching `branch` to an existing
  `ChangeSummary` instance uses `.model_copy(update={...})`, not `.copy()`.

## What We're NOT Doing

- Discovering a change that exists *only* inside a worktree and not yet in
  the main checkout — correlation only checks worktrees against change_ids
  already known from the main checkout's `list_changes()` result.
- Any change to the `/10x-*` skills or CLAUDE.md conventions (a separate,
  earlier line of investigation for this same change-id concluded no skill
  changes were needed; this plan is the actual feature request that
  superseded that conclusion).
- A remedy path for "I already created a worktree before committing" —
  explicitly descoped by the user during questioning.
- Caching or debouncing git calls — matches the existing pattern where
  `get_project_statuses()` already recomputes everything fresh on every
  request.
- A visible error/warning UI state for git failures — failures fall back
  silently to today's behavior (existing `get_next_10x_action` per-project
  `except Exception` pattern).

## Implementation Approach

Add a small, dependency-free worktree-detection module that shells out to
`git worktree list --porcelain` and reuses the existing `list_changes()`
function against each worktree path to find matches. Thread the result
through `project_status.py` (as the source of truth for a matched change's
`ChangeSummary`) and into `workflow_recommendations.py` (as a `branch` label
on the resulting `WorkflowRecommendation`). Restructure the one
multi-active-change code path so it returns a list instead of a single
blocked entry. Render the new field in the existing list-rendering code in
`dist/app.js`.

## Critical Implementation Details

- **Existing test must be rewritten, not just supplemented**:
  `tests/test_workflow_recommendations.py::test_multiple_active_changes_block_a_command`
  (line 136) currently asserts a single recommendation with
  `candidates == ["first", "second"]`. Under the new behavior, two active
  changes with no worktree now produce **two** individually-blocked
  recommendations (`candidates == ["first"]` and `candidates == ["second"]`
  respectively), not one combined entry. This test's assertions must change
  as part of Phase 2, not be left passing by accident.
- **Git-failure fallback is load-bearing, not optional**: every existing
  fixture project in both test files is a plain directory, not a git repo.
  `git -C <path> worktree list --porcelain` will exit non-zero for all of
  them. The worktree-detection function must catch that (and
  `FileNotFoundError` if git itself is missing) and return "no worktrees"
  rather than raise — otherwise every existing passing test breaks.

## Phase 1: Worktree Detection & Data Model

### Overview

Add the git-worktree-to-change correlation as a standalone, testable unit,
and thread the resulting `branch` metadata onto `ChangeSummary`.

### Changes Required:

#### 1. New worktree detection module

**File**: `app/worktrees.py`

**Intent**: Given a project's root path, list its linked git worktrees
(excluding the main one), then find which of those worktrees contains a
given active change_id's folder, reusing the existing `list_changes`
function to read that worktree's own change data.

**Contract**:
- `list_project_worktrees(project_path: Path) -> list[tuple[Path, str | None]]`
  — runs `git -C <project_path> worktree list --porcelain`, parses
  `worktree <path>` / `branch refs/heads/<name>` blocks (branch is `None`
  for a `detached` entry), skips the entry whose path equals
  `project_path.resolve()` (the main worktree), and returns `(path, branch)`
  pairs for the rest. Ignores any other line it doesn't recognize within a
  block (e.g. `locked <reason>`, `bare`, `prunable <reason>`) rather than
  assuming a fixed line count per block — this repo's own
  `.claude/worktrees/archive-project` entry is `locked` and must still
  parse correctly. Catches `subprocess.CalledProcessError` and
  `FileNotFoundError` and returns `[]` on either (see Critical
  Implementation Details).
- `get_worktree_branch_map(project_path: Path, change_ids: set[str]) -> dict[str, tuple[str, ChangeSummary]]`
  — for each worktree from `list_project_worktrees`, calls
  `list_changes(worktree_path / "context")`, and for each returned summary
  whose `change_id` is in `change_ids` and not already claimed by an
  earlier worktree, records `change_id -> (branch, summary)`.

#### 2. Add `branch` to the change data model

**File**: `app/changes.py`

**Intent**: Let a `ChangeSummary` carry which branch (if any) is currently
processing it, mirroring how `phase_progress` and `roadmap_correlation` are
already attached per-summary.

**Contract**: Add `branch: str | None = None` to `ChangeSummary`. No change
to `_parse_change_md` or `list_changes` themselves — `branch` is populated
later, by whichever caller has git/project-path context.

#### 3. Wire correlation into project status

**File**: `app/project_status.py`

**Intent**: After computing the main checkout's `changes` list, look up
worktree correlations for those change_ids and, for each match, replace
that entry with the worktree's own `ChangeSummary` (the worktree becomes
the source of truth for status), stamped with its `branch`.

**Contract**: In `get_project_status`, after `list_changes(...)`, call
`get_worktree_branch_map(project_path, {c.change_id for c in changes})`.
For each match, replace the corresponding entry in `changes` with
`worktree_summary.model_copy(update={"branch": branch})`.

### Success Criteria:

#### Automated Verification:

- [ ] New `tests/test_worktrees.py` passes: covers no-git-repo fallback, a
      repo with no linked worktrees, a repo with one linked worktree that
      matches an active change_id, and a linked worktree whose change_id
      isn't in the requested set.
- [ ] `tests/test_changes.py` still passes with `branch` defaulting to
      `None` on parsed summaries.
- [ ] `tests/test_projects.py` and existing `test_api.py` project-status
      tests still pass unchanged (non-git fixtures fall back cleanly).
- [ ] `uv run pytest` passes.

#### Manual Verification:

- This repo already has a real example ready to use for this check:
  `.claude/worktrees/archive-project` (branch `worktree-archive-project`,
  currently `locked`) with its own
  `context/changes/archive-project/change.md`. Call `get_project_status`
  against `D:/repos/10xtracker` in a REPL and confirm the returned
  `ChangeSummary` for `archive-project` has `branch == "worktree-archive-project"`
  and reflects that worktree's `change.md` content. Remember this worktree
  was created by Claude Code's own tooling for a live session — do not
  remove or unlock it as part of this verification.

---

## Phase 2: Recommendation Engine Restructure

### Overview

Change the multi-active-change path from a single blocked entry into one
recommendation per active change, and surface `branch` on the recommendation
itself.

### Changes Required:

#### 1. Recommendation model and per-change branch threading

**File**: `app/workflow_recommendations.py`

**Intent**: `WorkflowRecommendation` gains a `branch` field. Every
recommendation built for a specific change_id (real or blocked) carries
that change's `branch` when known, so the branch is visible regardless of
whether the change ended up actionable or still blocked.

**Contract**: Add `branch: str | None = None` to `WorkflowRecommendation`.
`_recommend_for_active_change` gains a `branch: str | None = None`
parameter and passes it into every `WorkflowRecommendation(...)` it
constructs.

#### 2. Multi-change control flow

**File**: `app/workflow_recommendations.py`

**Intent**: `_recommend_for_project` returns `list[WorkflowRecommendation]`
instead of a single value. When more than one change is active, each change
gets its own entry: worktree-backed changes call
`_recommend_for_active_change(..., branch=change.branch)` for a real
command; changes with no worktree (`change.branch is None`) get an
individual `_blocked(project, "Which change can be worked on next?", candidates=[change.change_id])`
entry instead of being lumped into one combined blocked entry. The
single-active-change and roadmap-eligible-change paths are unchanged except
each now returns a one-item list, and pass `branch=active_change.branch`
where a change is involved.

**Contract**: `get_next_10x_action` changes its
`recommendations.append(_recommend_for_project(project))` to
`recommendations.extend(_recommend_for_project(project))` (the exception
fallback path stays a single-item append via `_blocked`, wrapped in a list
by the append itself since it's already one recommendation).

### Success Criteria:

#### Automated Verification:

- [ ] `tests/test_workflow_recommendations.py::test_multiple_active_changes_block_a_command`
      is rewritten to assert two individually-blocked recommendations
      (see Critical Implementation Details) — do not leave the old
      single-entry assertion in place.
- [ ] New test: two active changes, one with a matching worktree, produces
      exactly two recommendations — one with `command` set and `branch`
      matching the worktree's branch, one blocked with
      `candidates == [<the other change_id>]`.
- [ ] New test: single active change with a matching worktree still
      returns exactly one recommendation, with `branch` set.
- [ ] All existing `test_workflow_recommendations.py` cases still pass
      (single-active-change and roadmap-selection paths unchanged in
      behavior, only in return-type wrapping).
- [ ] `uv run pytest` passes.

#### Manual Verification:

- Hit `GET /api/recommendations` against a project with two active
  changes, one backed by a real worktree, and visually confirm the JSON
  shape matches the automated test's expectation.

---

## Phase 3: Frontend Rendering

### Overview

Show the `branch` label in the next-action panel.

### Changes Required:

#### 1. Render branch alongside the command

**File**: `dist/app.js`

**Intent**: When a recommendation has a `branch`, show it as a `(branch)`
prefix next to the rendered command, following the existing element-creation
pattern used for `candidates`/`candidate_commands` at lines 399-422.

**Contract**: Wherever the recommendation's `command` is currently rendered
into the DOM, check `recommendation.branch` and, if present, prepend a
small text node or span reading `(${recommendation.branch})` before the
command text — matching the existing DOM-construction style in this file
(no new dependencies, no build step).

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest` still passes (no backend regression).

#### Manual Verification:

- Load the dashboard in a browser against a project with a worktree-backed
  active change and confirm the branch name is visibly rendered next to
  its command.
- Confirm a recommendation with no `branch` (today's normal case) renders
  exactly as before, with no stray `(None)` or empty parentheses.

---

## Phase 4: End-to-End Test

### Overview

Prove the whole path — real git repo, real `git worktree add`, real API
call — works together, since Phases 1-3 are each tested in isolation.

### Changes Required:

#### 1. Real-worktree API test

**File**: `tests/test_api.py`

**Intent**: Add a fixture that turns a fixture project into an actual git
repo (`git init`, one commit), creates a second active change directly in
the main checkout, then uses `git worktree add` to create a linked worktree
whose own `context/changes/<other-id>/change.md` exists, and asserts
`GET /api/recommendations` returns two entries as designed.

**Contract**: New test function using `subprocess.run` (or the existing
project's preferred subprocess helper, if any) to drive `git init` /
`git add` / `git commit` / `git worktree add` inside `tmp_path`, mirroring
the existing `_make_fixture_project` helper style already in this file.

### Success Criteria:

#### Automated Verification:

- [ ] New end-to-end test passes: `GET /api/recommendations` on the
      worktree-backed fixture returns one entry with `branch` set and a
      real `command`, and one blocked entry for the non-worktree change.
- [ ] Full suite passes: `uv run pytest`.

#### Manual Verification:

- None beyond what Phases 1-3 already covered manually — this phase is
  purely automated proof the pieces integrate.

**Implementation Note**: After this phase's automated verification passes,
pause for manual confirmation before considering the change complete.

---

## Testing Strategy

### Unit Tests:

- `app/worktrees.py`: git-failure fallback, no-worktrees case,
  matching/non-matching worktree correlation.
- `app/workflow_recommendations.py`: per-change branch threading through
  every recommendation path, multi-change list restructure.

### Integration Tests:

- `tests/test_api.py` end-to-end test using a real git repo + real
  `git worktree add` (Phase 4).

### Manual Testing Steps:

1. Track a real project with two active changes.
2. Create a `git worktree add` checkout for one of them with its own
   `context/changes/<id>/change.md`.
3. Load the dashboard and confirm the branch label appears next to that
   change's recommendation, and the other change still shows as blocked.

## Performance Considerations

None beyond what already exists — recommendations are recomputed fresh on
every request today, and this plan adds one more subprocess call per
project per request, matching that existing no-caching pattern.

## Migration Notes

None — `branch` is a new optional field on both `ChangeSummary` and
`WorkflowRecommendation`, defaulting to `None`; existing consumers of these
models are unaffected.

## References

- Frame brief: `context/changes/support-worktrees/frame.md` (documents the
  earlier, narrower doc-only conclusion this plan supersedes)
- `app/changes.py:65` — `list_changes`, reused directly against worktree
  paths
- `app/project_status.py:15` — `get_project_status`, correlation wiring
  point
- `app/workflow_recommendations.py:174-232` — `_recommend_for_project`,
  the code being restructured
- `dist/app.js:399-422` — existing candidate-list rendering pattern
- `tests/test_workflow_recommendations.py:136` — test requiring rewrite

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Worktree Detection & Data Model

#### Automated

- [x] 1.1 New tests/test_worktrees.py passes (fallback, no-worktrees, match, non-match cases)
- [x] 1.2 tests/test_changes.py still passes with branch defaulting to None
- [x] 1.3 tests/test_projects.py and existing test_api.py project-status tests still pass unchanged
- [x] 1.4 uv run pytest passes

#### Manual

- [x] 1.5 Manual worktree created; get_project_status reflects worktree's change.md and branch

### Phase 2: Recommendation Engine Restructure

#### Automated

- [ ] 2.1 test_multiple_active_changes_block_a_command rewritten for two individually-blocked recommendations
- [ ] 2.2 New test: worktree-backed + non-worktree active changes produce two correctly-shaped recommendations
- [ ] 2.3 New test: single active change with worktree returns one recommendation with branch set
- [ ] 2.4 All existing test_workflow_recommendations.py cases still pass
- [ ] 2.5 uv run pytest passes

#### Manual

- [ ] 2.6 GET /api/recommendations manually verified against a two-active-change project

### Phase 3: Frontend Rendering

#### Automated

- [ ] 3.1 uv run pytest still passes

#### Manual

- [ ] 3.2 Branch name visibly rendered next to its command in the dashboard
- [ ] 3.3 Recommendation with no branch renders unchanged, no stray placeholder text

### Phase 4: End-to-End Test

#### Automated

- [ ] 4.1 New end-to-end test passes (real git repo + git worktree add)
- [ ] 4.2 Full suite passes: uv run pytest

#### Manual

- [ ] 4.3 Final confirmation the change is complete
