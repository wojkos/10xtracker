# Worktree-Aware Recommendations — Plan Brief

> Full plan: `context/changes/support-worktrees/plan.md`
> Frame brief: `context/changes/support-worktrees/frame.md`

## What & Why

10xtracker's dashboard recommends the next `/10x-*` command per tracked
project, but today it just blocks with "which change can be worked on
next?" whenever more than one change is active — exactly the situation that
happens once you start using git worktrees to work on changes in parallel.
This plan makes the recommendation engine detect those worktrees, read each
one's own `change.md` as the authoritative status for the change it's
processing, and show a real, branch-labeled recommendation for each active
change instead of one generic block.

## Starting Point

An earlier framing pass on this change-id concluded no code was needed —
just a documentation convention about committing before creating a
worktree. During planning, the user clarified they actually want the app
itself to detect worktrees and surface them in the dashboard; this plan
supersedes that earlier, narrower conclusion. The current code
(`app/workflow_recommendations.py`) has one hook point ready-made for this:
the `len(active_changes) > 1` branch that already lists candidates — it
just blocks today instead of acting.

## Desired End State

Track a project with two active changes, one of them being worked on in a
`git worktree add` checkout. The dashboard now shows two entries: one real,
actionable command labeled with its branch name, and one "which one next"
prompt for the change that has no worktree yet — instead of a single
generic block naming both.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Worktree-to-change correlation | Path-match: a worktree "claims" a change_id if `context/changes/<id>/` exists there | Matches how the file-based change system already works, no new naming convention | Plan (user-confirmed) |
| Multiple active changes | One recommendation per change, not one combined block | Directly extends the existing multi-change branch instead of an all-or-nothing block | Plan (user-confirmed) |
| Status source of truth | Worktree's `change.md` wins over the main checkout's copy | Matches "update change from this branch" — the worktree is where the work is happening | Plan (user-confirmed) |
| Branch label placement | New `branch` field on the response model, not string-mangled into `command` | Keeps `command` a literal, copy-pasteable `/10x-*` invocation | Plan (user-confirmed) |
| Git failure handling | Silently fall back to today's behavior | Every existing test fixture is a plain (non-git) directory — this is required for backward compatibility, not just a preference | Plan (user-confirmed) |
| Change-creation-before-worktree doc gap | Superseded — real feature built instead | The frame's doc-only fix no longer covers what's actually wanted | Frame → Plan |

## Scope

**In scope:**
- Git worktree detection for a tracked project (`app/worktrees.py`)
- Correlating a worktree to an active change_id by path match
- Using the worktree's `change.md` as that change's status source
- One recommendation per active change (real + branch, or individually blocked)
- Dashboard rendering of the branch label
- End-to-end test with a real git repo + real `git worktree add`

**Out of scope:**
- Discovering changes that exist only inside a worktree, not yet in the main checkout
- Any `/10x-*` skill or CLAUDE.md changes
- A recovery path for "I already made the worktree before committing"
- Caching git calls, or a visible error state for git failures

## Architecture / Approach

A new `app/worktrees.py` module shells out to `git worktree list --porcelain`
and reuses the existing `list_changes()` function against each worktree's
own `context/` directory — no new frontmatter-parsing code. That result
flows into `project_status.py` (replacing a matched change's summary with
the worktree's version) and into `workflow_recommendations.py` (attaching
`branch` to the resulting recommendation, and returning a list instead of a
single value when multiple changes are active). `dist/app.js` renders the
new field using its existing list-rendering pattern.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Worktree Detection & Data Model | `app/worktrees.py` + `branch` on `ChangeSummary`, wired into project status | Silent fallback must hold for every non-git fixture already in the test suite |
| 2. Recommendation Engine Restructure | Per-change recommendations instead of one block; `branch` on `WorkflowRecommendation` | An existing test (`test_multiple_active_changes_block_a_command`) asserts the *old* behavior and must be rewritten, not left passing by accident |
| 3. Frontend Rendering | `(branch)` label shown in the next-action panel | None significant — small, isolated DOM change |
| 4. End-to-End Test | Real git repo + `git worktree add` proving the whole path works | None significant — proof phase only |

**Prerequisites:** None — builds directly on existing code, no new dependencies.
**Estimated effort:** ~1 session across 4 phases (small, well-scoped feature).

## Open Risks & Assumptions

- Assumes the 10xtracker backend process has local filesystem access to
  every linked worktree's path (true for the local-dashboard use case this
  app already serves).
- Assumes `git worktree list --porcelain`'s format is stable across the
  git versions in use — confirmed against this repo's git, not exhaustively
  version-tested.

## Success Criteria (Summary)

- A project with a worktree-backed active change shows a real command with
  its branch name, not a generic block.
- A project with multiple active changes but no worktrees behaves exactly
  as it does today (individually, per change).
- The full existing test suite passes, including the rewritten
  multi-active-change test.
