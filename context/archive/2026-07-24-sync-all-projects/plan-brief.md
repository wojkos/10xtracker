# Sync All Projects — Plan Brief

> Full plan: `context/changes/sync-all-projects/plan.md`
> Related: `context/archive/2026-07-23-manual-single-project-sync/plan-brief.md` (S-06)
> Roadmap: `context/foundation/prd.md` (FR-007)

## What & Why

Add a global "Sync All" button to refresh all tracked projects in parallel with a single click, instead of clicking individual "Refresh" buttons for each project. This is roadmap item **S-07**, the second sync feature after S-06's per-project refresh.

## Starting Point

**S-06** (Manual Single-Project Sync) provides per-project "Refresh" buttons that call `GET /api/projects` and update individual projects. These work well, but require multiple clicks for multi-project workflows. S-07 consolidates this into one button that syncs all projects concurrently.

## Desired End State

Developer clicks "Sync All" at the top of the dashboard. All projects refresh in parallel within 1-2 seconds (same time as refreshing the slowest single project, since they run concurrently, not sequentially). If any projects fail, a summary message shows which ones and why; successful projects remain updated. Developer can click again immediately.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Button placement | Top of page, next to dashboard title | Prominent and discoverable for frequent use. | User input |
| Loading indicator | Global spinner near button + disable button | Clear visual feedback that sync is in progress. | User input |
| Concurrency | All projects in parallel via `Promise.allSettled()` | Responsive UX — total time ≈ slowest single project, not N × slowest. | Plan |
| Failure handling | Show summary ("Synced 4/5 projects. X failed: [reason]") + keep successful projects updated | User knows what worked and what didn't. Matches S-06's per-project error isolation. | User input |
| Button state | Disable "Sync All" + all individual "Refresh" buttons during sync | Prevents concurrent/conflicting syncs. Simpler state tracking. | User input |

## Scope

**In scope:**
- "Sync All" button in new `<div id="dashboard-controls">` at top of dashboard
- Concurrent `fetch()` calls for all projects using `Promise.allSettled()`
- Global spinner/loading indicator while sync is in flight
- Summary message showing success/failure counts and error details
- Disable individual refresh buttons during sync-all
- Re-enable all buttons after sync completes

**Out of scope:**
- New API endpoint (reuse existing `GET /api/projects`)
- Persistent "last synced" timestamps
- Retry logic on failure
- Selective project syncing (sync only checked projects)
- Autosync triggering (autosync uses existing S-08 timer, separate from manual sync-all)

## Architecture / Approach

Pure frontend: new `syncAllProjects()` function that collects all project paths from the DOM, calls `syncProject(path)` for each in parallel, waits for all to complete, and displays a summary. Reuses all existing patterns from S-06 — no backend changes. Global `syncingAll` flag coordinates button state across the page.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. HTML & state | "Sync All" button + global status div + `syncingAll` flag | Simple; risk is button not wired to handler. |
| 2. Sync logic | `syncAllProjects()` function + refactor `syncProject()` to return result object + update `updateProjectUI()` | Moderate; must handle concurrent Promise results correctly and extract error details. |
| 3. Styling | CSS for button and status message | Low; purely cosmetic. |

**Prerequisites:** S-06 must be merged (per-project refresh implemented and working)
**Estimated effort:** ~1 session across 3 phases; build on S-06's patterns closely.

## Open Risks & Assumptions

- **Assumption:** S-06 is complete and the per-project refresh code is stable. If S-06 changes, the approach to parallel syncing may need adjustment.
- **Risk:** If there are many projects (10+), parallel `fetch()` requests might hit browser limits; acceptable for v1 (app targets 1-10 projects per the PRD).
- **Assumption:** Vanilla JS `Promise.allSettled()` is sufficient for coordinating results. If a framework is added later, this pattern may need refactoring into component state.

## Success Criteria (Summary)

- Developer clicks "Sync All" and all projects refresh concurrently within 1-2 seconds
- Summary message correctly reports "Synced X/Y projects" or shows partial failures
- Individual refresh buttons are disabled during sync; re-enabled after
- Can click "Sync All" again immediately after completion
