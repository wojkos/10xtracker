# Manual Single-Project Sync — Implementation Plan

## Overview

Add a per-project "Refresh" button to the dashboard that explicitly triggers a re-read of that project's `context/changes/` directory and updates the changes list in place. Currently, `GET /api/projects` always reads fresh from disk, but there's no explicit UI action to trigger it — S-06 makes the refresh action visible and user-initiated. This is a lightweight UI + minimal backend change; the data-reading logic is already working from S-01.

## Current State Analysis

- S-01 (`project-change-status-view`) is implementing and will provide:
  - `/api/projects` endpoint that reads all tracked projects fresh on each GET call.
  - A project list rendering with changes and statuses.
  - Per-project error handling (malformed `change.md` shown inline).
- No refresh/sync UI exists yet — users can only see data as it was when the page loaded or last refreshed.
- The app currently has no loading states, spinners, or async UI feedback patterns.
- Per `tech-stack.md`, the frontend is vanilla JS against a JSON API (no framework).

### Key Discoveries:

- S-01's `GET /api/projects` is intentionally read-every-time (no caching), so reusing it for explicit refresh avoids new backend code and keeps the refresh mechanism simple.
- S-01's error handling already supports per-project failure surfacing (`error: str | None` in the `ChangeSummary` model), so sync failures can be shown inline without removing the project.
- Vanilla JS can handle concurrent fetch calls, making parallel per-project syncing natural (no framework overhead).

## Desired End State

A developer can click a "Refresh" button on any tracked project in the dashboard. While the refresh is in flight, a small spinner or "Refreshing..." text indicates activity. When the refresh completes, the project's change list updates in place with fresh data from disk. If a sync fails (e.g., path no longer exists), an inline error message appears below the project, allowing the user to retry, fix the path, or remove the project manually. Multiple projects can be refreshed concurrently — clicking "Refresh" on one project does not block others.

**Verification**: Run the app, add a project, manually edit a `change.md` file outside the app (change the status field), click "Refresh" on that project in the browser, confirm the UI updates to show the new status, and the change list reflects the change within 1-2 seconds.

### Key Discoveries:

- Reusing `GET /api/projects` means the refresh button re-fetches all tracked projects but updates only the clicked project in the UI — acceptable for v1 (1-10 projects per PRD).
- No persistent state needed — in-memory loading flags per project suffice. Page reload resets them (acceptable because reload itself re-fetches all data).
- S-01's Pydantic response models already include `error: str | None` per change, so sync errors can propagate naturally without new model fields.

## What We're NOT Doing

- No new API endpoint — reuse `GET /api/projects` instead of adding `POST /api/projects/{id}/sync`.
- No persistent "last synced" timestamps — in-memory state only.
- No retry logic on failure — show the error and let the user decide next steps.
- No auto-removal of broken projects on sync failure — keep the project in the list so the user can fix it or remove it manually.
- No `localStorage` persistence of sync state — loading flags reset on page reload (aligns with S-01's pattern).
- No "sync all" button yet — S-07 adds that as a separate feature.

## Implementation Approach

Minimal frontend addition: add a "Refresh" button per project, track per-project loading state in JS variables, and re-call `GET /api/projects` on click, updating only that project's section with the new response. Use CSS or simple text changes for the loading indicator (no new dependencies). Error messages are surfaced inline, matching S-01's pattern.

## Critical Implementation Details

**Per-project fetch and update**: When the user clicks "Refresh" on a project, fetch all projects (to keep backend logic simple), but only update the DOM for the clicked project. The response includes all projects, but the UI update is scoped to one. This avoids backend complexity while keeping the UX focused.

**Concurrent requests**: Each project's `fetch()` is independent — clicking "Refresh" on project A while project B is still loading just starts a new fetch for A. Both can be in flight. Track loading state per project ID (e.g., `loadingProjects: Set<string>()`) to enable/disable buttons and show spinners per project.

## Phase 1: Frontend UI — Refresh Button & Loading State

### Overview

Add a "Refresh" button to each project in `dist/app.js`, wire it to trigger a fresh `GET /api/projects` call, and update only that project's DOM section with the response. Track per-project loading state to show/hide spinners and disable buttons during fetch.

### Changes Required:

#### 1. `dist/index.html`

**Intent**: Add a refresh button per project in the rendered project container and an error display area for sync failures.

**Contract**: Each project section gets a `<button class="refresh-btn">Refresh</button>` and an empty `<div class="sync-error"></div>` (initially hidden). Button and error container are part of the project header/summary, not mixed into the changes list. Button is disabled (`disabled` attribute) while sync is in flight.

#### 2. `dist/app.js`

**Intent**: Implement the refresh logic — fetch projects, update the clicked project in place, and manage per-project loading state.

**Contract**: Adds a `syncProject(projectPath: string)` function that:
- Sets the project's loading flag to `true` (enables the spinner, disables the button).
- Calls `fetch('/api/projects')` (reuses the same GET endpoint).
- On success, finds the returned project matching `projectPath` and updates only that project's DOM section with fresh changes and clears any previous sync error.
- On error, displays the error message in the sync-error div and leaves the project in the list.
- Sets the project's loading flag to `false` when done (disables spinner, re-enables button).
- Stores loading state in a `Set<string>` (project paths) to track which projects are currently syncing.

Button click handler calls `syncProject(projectPath)` with the project's path as the argument.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run python -c "import app.main"` succeeds (no backend regression)
- [ ] `curl http://127.0.0.1:8000/` returns HTTP 200 with the updated HTML (frontend files present and served)

#### Manual Verification:

- [ ] Browser: Open `http://127.0.0.1:8000/`, add a project, click "Refresh" button — verify spinner/text shows while fetching
- [ ] Browser: Wait for refresh to complete; changes list updates with fresh data
- [ ] Browser: Manually edit a `change.md` file in the project directory (change status or title), click "Refresh" again, confirm the UI updates to show the edit within 1-2 seconds
- [ ] Browser: Click "Refresh" on multiple projects concurrently; verify all load in parallel (no blocking)
- [ ] Browser: Simulate a sync error by renaming the project directory, click "Refresh"; verify error message appears inline without removing the project from the list

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before marking the change as complete.

---

## Testing Strategy

### Unit Tests:

No new unit tests required — the refresh logic is pure DOM manipulation and `fetch()` calls, best verified end-to-end in the browser.

### Integration Tests:

No changes to backend tests — S-01's existing test suite covers the data layer.

### Manual Testing Steps:

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/`, add a local 10xDEV project.
3. Click the "Refresh" button on that project.
4. Confirm the spinner appears and the changes list updates.
5. Repeat click on the same project while still loading — verify no double-fetch (button disabled during load).
6. Edit a `change.md` file in the tracked project outside the app.
7. Click "Refresh" again — confirm the change appears in the UI within 1-2 seconds.
8. Test error case: rename the project directory to break the path, click "Refresh", confirm inline error.

## Performance Considerations

Minimal — each refresh is a single HTTP GET to `/api/projects` (same as existing page load). Concurrency is naturally handled by the browser's fetch queue. At v1 scale (1-10 projects, 20-50 changes each), latency should be sub-second on typical local I/O.

## Migration Notes

None — purely additive UI feature; no data changes or persisted state migrations needed.

## References

- Roadmap: `context/foundation/roadmap.md` (S-06: Manual single-project sync)
- PRD: `context/foundation/prd.md` (FR-006)
- S-01 plan: `context/changes/project-change-status-view/plan.md` (data layer, API contract)
- Frontend (to extend): `dist/index.html`, `dist/app.js` (S-01 Phase 3 deliverables)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Frontend UI — Refresh Button & Loading State

#### Automated

- [ ] 1.1 `uv run python -c "import app.main"` succeeds
- [ ] 1.2 `curl http://127.0.0.1:8000/` returns HTTP 200

#### Manual

- [ ] 1.3 Browser: Click "Refresh", spinner appears, data updates
- [ ] 1.4 Browser: External `change.md` edit appears after refresh
- [ ] 1.5 Browser: Concurrent syncs work (multiple projects refresh in parallel)
- [ ] 1.6 Browser: Sync error shows inline without removing project
