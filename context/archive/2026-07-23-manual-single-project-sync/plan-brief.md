# Manual Single-Project Sync — Plan Brief

> Full plan: `context/changes/manual-single-project-sync/plan.md`
> Roadmap: `context/foundation/roadmap.md` (S-06)
> Related: `context/changes/project-change-status-view/plan.md` (S-01, data layer)

## What & Why

Add a "Refresh" button to each project in the dashboard that explicitly triggers a re-read of that project's changes from disk. Currently, the backend reads fresh on every page load, but there's no UI action for the user to force a refresh without reloading. S-06 makes refresh user-initiated and visible, unblocking S-07 (sync all) and S-08 (autosync).

## Starting Point

S-01 (`project-change-status-view`) provides a list of tracked projects and their changes, read fresh from disk via `GET /api/projects` on each call. The frontend renders the list, but there's no way to refresh a single project's data without reloading the page. Existing per-project error handling (from S-01) already supports inline failure messages, so sync errors can surface naturally.

## Desired End State

Developer clicks a "Refresh" button on any project. A spinner briefly appears while the data is fetched. The project's change list updates in place with fresh data from disk within 1-2 seconds. If a sync fails (path gone, permission error), an inline error message appears without removing the project — the user can retry or remove it manually. Multiple projects can be synced concurrently.

## Key Decisions Made

| Decision                  | Choice                          | Why                                                                                  | Source |
| ----------------------- | ------------------------------- | -------------------------------------------------------------------------------------- | ------ |
| API approach              | Reuse GET /api/projects         | Zero new backend code; refresh mechanism already works and is tested in S-01. Scales acceptably for v1 (1-10 projects). | Plan   |
| Loading indicator         | Inline spinner/text per button  | Minimal UI, tells user something is happening. Simpler than toast messages.           | Plan   |
| Sync timestamps           | None (v1 skips them)            | Simpler UI. User can infer freshness from the data. Timestamps add complexity without clear value at this scale. | Plan   |
| State persistence         | In-memory only                  | No localStorage overhead. Loading state resets on reload (acceptable — reload re-fetches anyway).   | Plan   |
| Error handling            | Inline message, keep project    | User can decide to retry, fix path, or remove. Matches S-01's error pattern.          | Plan   |
| Concurrency               | Parallel (independent per project) | Responsive UX. Natural for fetch(). More complex state tracking but worth the responsiveness. | Plan   |

## Scope

**In scope:**
- Add "Refresh" button per project in the UI
- Track per-project loading state in JavaScript
- Call `GET /api/projects` on button click
- Update only the clicked project's DOM with fresh data
- Show spinner/loading text while fetch is in flight
- Display sync errors inline without removing the project

**Out of scope:**
- New API endpoint — reuse existing GET
- "Sync all" button — that's S-07
- Autosync timer — that's S-08
- Persistent "last synced" timestamps
- Automatic project removal on sync failure
- Retry logic on failure
- localStorage persistence of sync state

## Architecture / Approach

Pure frontend addition: add a button to each project's rendered section, wire its click handler to call `fetch('/api/projects')`, extract the updated project from the response, and update only that project's DOM. Track loading state per project ID in a JavaScript `Set` to manage button enabled/disabled state and spinner visibility. Error messages from the backend populate an inline error div below the project name.

No new backend code needed — reuse S-01's existing endpoint and error handling. Concurrency is natural because each `fetch()` is independent; the browser queues them and the UI updates as each completes.

## Phases at a Glance

| Phase | What it delivers                           | Key risk                                  |
| ----- | ------------------------------------------- | ----------------------------------------- |
| 1     | Refresh button per project, loading state  | DOM update logic has off-by-one or scope errors; test carefully with manual edits |

**Prerequisites:** S-01 must be merged and the frontend UI from Phase 3 must be in place
**Estimated effort:** ~1 session; ~1 hour hands-on work

## Open Risks & Assumptions

- **Assumption:** S-01's `GET /api/projects` endpoint is complete and working by the time this plan executes. If S-01's API contract changes (response shape, status codes), this plan's fetch logic must adjust.
- **Risk:** Manually edited `change.md` files might not be recognized by the filesystem immediately on all platforms (cache lag). Refresh should show fresh data, but if it doesn't, the issue is file-system latency, not the app.
- **Assumption:** Vanilla JS `fetch()` is sufficient for concurrent requests. If future phases add a framework (React, Vue), this plan's state management will need refactoring into component state.

## Success Criteria (Summary)

- User can click "Refresh" on a project and see fresh data appear in the UI within 1-2 seconds
- Multiple projects can be synced concurrently without blocking each other
- Sync failures (broken path, permission error) show an inline message without removing the project
