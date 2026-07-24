# Sync All Projects Implementation Plan

## Overview

Add a global "Sync All" button that refreshes all tracked projects concurrently in a single action. The button appears at the top of the dashboard, shows a spinner while syncing, and displays a summary message if any projects fail. This builds on **S-06** (Manual Single-Project Sync), which added per-project "Refresh" buttons.

## Current State Analysis

**What exists:**
- Per-project "Refresh" buttons already implemented (S-06) using `syncProject(projectPath)` in `dist/app.js`
- Each refresh calls `GET /api/projects` and updates only the clicked project's DOM
- A global `loadingProjects` Set tracks which projects are currently refreshing
- Individual refresh buttons are disabled while their project is syncing
- Per-project error handling with inline error divs (`.sync-error`)
- Autosync settings and timer already exist (S-08) via `/api/settings`

**What's missing:**
- No global "Sync All" button to refresh all projects at once
- No UI for showing overall sync progress or summary results
- No mechanism to coordinate disabling individual buttons during a global sync
- No way to show partial-failure messages (e.g., "Synced 4/5 projects")

## Desired End State

When the user clicks "Sync All" at the top of the dashboard:
1. The button disables, all individual refresh buttons disable, and a global spinner appears
2. All projects sync **concurrently** (not sequentially) via parallel `fetch()` calls
3. As each project completes, its data updates in place; the UI reflects changes immediately
4. If one project fails, its error appears inline (existing per-project error div), but successful projects remain updated
5. When all syncs complete, a summary message appears: "Synced 5/5 projects" or "Synced 4/5 projects. Project X failed: [reason]"
6. Button re-enables, individual refresh buttons re-enable
7. Developer can click "Sync All" again immediately after

## Key Discoveries:

- **Frontend state management:** Global `loadingProjects` Set already handles per-project state; extend with a separate `syncingAll` boolean flag for global sync state
- **Concurrent pattern:** S-06 already uses `fetch()` for each project independently; S-07 uses `Promise.all()` to coordinate all fetches and wait for completion
- **Error handling pattern:** S-06's per-project error display is reusable; "Synced X/Y" summary goes in a new global error/status div
- **HTML structure:** Currently `<h1>10xDevTracker</h1>` followed by autosync controls; add "Sync All" button to a new `<div id="dashboard-controls">` right after the title
- **API reuse:** No new backend endpoints needed; reuse `GET /api/projects` — this is the same S-06 pattern

## What We're NOT Doing

- Creating a new API endpoint (reuse existing `GET /api/projects`)
- Adding persistent "last synced" timestamps (v2+ feature)
- Implementing retry logic for failed projects (user can click "Sync All" again)
- Queueing syncs (if a sync-all is in progress and user clicks again, ignore the click)
- Adding filters or selective project syncing

## Implementation Approach

Pure frontend addition in `dist/app.js`:

1. **Add a global sync state flag** (`let syncingAll = false`) to track whether a global sync is in progress
2. **Create a new `syncAllProjects()` function** that:
   - Extracts all project paths from the DOM
   - Sets `syncingAll = true` and disables all buttons via `updateProjectUI()` 
   - Calls `syncProject(path)` for each project and collects the Promises
   - Uses `Promise.all()` to wait for all syncs (or `Promise.allSettled()` to handle failures gracefully)
   - After all complete, compiles a summary: count successes/failures and extract error messages
   - Displays summary in a new global status div
   - Sets `syncingAll = false` and re-enables buttons
3. **Modify `updateProjectUI()`** to disable individual refresh buttons when `syncingAll` is true
4. **Add HTML elements** for:
   - "Sync All" button in a new `<div id="dashboard-controls">`
   - Global status message div (initially hidden, shows after sync completes)
5. **Add event listener** to the "Sync All" button that calls `syncAllProjects()` with guard against re-clicks during sync

## Phase 1: Frontend HTML & Global State

### Overview

Add the "Sync All" button to the HTML and prepare global state tracking for concurrent syncs.

### Changes Required:

#### 1. HTML Structure (`dist/index.html`)

**File**: `dist/index.html`

**Intent**: Add a new `<div id="dashboard-controls">` section right after the `<h1>` to hold the "Sync All" button. Add a global status message div to display sync results.

**Contract**: 
- Insert a new `<div id="dashboard-controls">` after `<h1>10xDevTracker</h1>` containing:
  - A `<button id="sync-all-btn">` with text "Sync All"
  - A `<span id="sync-all-status">` (initially empty) for the summary message
- Both should be visible by default and styled similarly to existing controls

#### 2. Global State Initialization (`dist/app.js`)

**File**: `dist/app.js`

**Intent**: Add a global flag to track whether a sync-all is in progress, so individual refresh buttons can be disabled during global sync.

**Contract**: 
At the top of `app.js` with the other global state variables:
- Add `let syncingAll = false;` to track global sync state

### Success Criteria:

#### Automated Verification:

- HTML validates: `dist/index.html` parses without errors
- No JavaScript syntax errors in modified `app.js`

#### Manual Verification:

- "Sync All" button visible at top of dashboard, right-aligned or next to autosync controls
- Button text reads "Sync All"
- Status message area is present below the button (initially empty)

---

## Phase 2: Core Sync Logic

### Overview

Implement the concurrent sync-all function and update state management to coordinate button disabling.

### Changes Required:

#### 1. `syncAllProjects()` Function (`dist/app.js`)

**File**: `dist/app.js`

**Intent**: Fetch and sync all projects concurrently, collect results, and display a summary message.

**Contract**: 
A new async function `syncAllProjects()` that:
- Extracts all project paths from the DOM: `document.querySelectorAll("article[data-project-path]").map(a => a.getAttribute("data-project-path"))`
- Sets `syncingAll = true`
- Creates an array of Promises by mapping each path to `syncProject(path)` — **BUT** modified to return a result object instead of void
- Uses `Promise.allSettled()` to wait for all to complete (captures both successes and failures)
- Counts results: `successes = results.filter(r => r.status === 'fulfilled').length; failures = results.length - successes`
- If `failures > 0`, extracts error messages from the rejected Promises or from the DOM `.sync-error` divs
- Displays summary: "Synced X/Y projects" or "Synced X/Y projects. Failed: [Project path: error]"
- Sets `syncingAll = false`
- Updates UI to re-enable buttons via `updateProjectUI()` (which checks `syncingAll`)

#### 2. Modify `syncProject()` Function (`dist/app.js`)

**File**: `dist/app.js`

**Intent**: Return a result object from `syncProject()` so the caller can track success/failure for the summary message.

**Contract**: 
- Refactor `syncProject(projectPath)` to return an object: `{ path: projectPath, success: boolean, error?: string }`
- On success: return `{ path: projectPath, success: true }`
- On error: return `{ path: projectPath, success: false, error: errorMessage }`
- The function's existing DOM-update logic remains the same; only the return value changes

#### 3. Modify `updateProjectUI()` Function (`dist/app.js`)

**File**: `dist/app.js`

**Intent**: Disable individual refresh buttons when a global sync is in progress.

**Contract**: 
- When `syncingAll` is true, disable all refresh buttons (not just the project being refreshed)
- Change the disable logic from: `refreshBtn.disabled = isLoading` to `refreshBtn.disabled = isLoading || syncingAll`

### Success Criteria:

#### Automated Verification:

- No JavaScript syntax errors after modifications
- All existing tests still pass (if tests exist)

#### Manual Verification:

- Click "Sync All" once; button disables and individual refresh buttons disable
- Spinner/status appears near the button
- All projects' data updates concurrently (watch for multiple changes appearing in quick succession)
- After a few seconds, status message appears: "Synced 5/5 projects" or similar
- Button and individual refresh buttons re-enable
- Can click "Sync All" again immediately and it works

---

## Phase 3: UI Styling & Polishing

### Overview

Add CSS styling for the new button and status message to match the existing dashboard design.

### Changes Required:

#### 1. CSS Styling (`dist/style.css`)

**File**: `dist/style.css`

**Intent**: Style the "Sync All" button and status message to be visually consistent with existing controls.

**Contract**: 
- Style `#dashboard-controls` as a flex container, right-aligned, with margin/padding matching existing control sections
- Style `#sync-all-btn` as a button matching the visual style of existing buttons (e.g., same colors, padding, hover state)
- Style `#sync-all-status` as a status message (small text, gray or accent color) with appropriate margin
- Ensure the status message spans multiple lines if there are multiple failed projects

### Success Criteria:

#### Automated Verification:

- CSS parses without syntax errors

#### Manual Verification:

- "Sync All" button looks visually consistent with other buttons on the page (e.g., "Refresh", "Remove")
- Status message text is readable and appropriately styled (not too large, not too small)
- Button and status message align properly with other controls at the top
- Responsive design: button and message remain visible and usable on smaller screens

---

## Testing Strategy

### Manual Testing Steps:

1. **Single sync-all action:**
   - Click "Sync All" button
   - Verify spinner appears and button disables
   - Verify all individual "Refresh" buttons are disabled
   - Wait for sync to complete
   - Verify status message shows "Synced X/5 projects" (or appropriate count)
   - Verify all projects' change lists updated with fresh data
   - Verify button and individual refresh buttons re-enable

2. **Partial failure handling:**
   - Remove one project's directory manually (e.g., rename folder) to simulate a missing path
   - Click "Sync All"
   - Verify the failed project shows an error in its error div
   - Verify successful projects' data updated normally
   - Verify status message shows "Synced 4/5 projects. Project X failed: ..."
   - Verify other projects remain functional

3. **Concurrent behavior:**
   - Add multiple projects (4-5) to the dashboard
   - Click "Sync All"
   - Watch the changes appear in quick succession (all in parallel, not one-at-a-time)
   - Verify individual "Refresh" buttons are disabled during sync
   - Verify status message correctly counts completions

4. **Re-click during sync:**
   - Click "Sync All", then immediately click again before it completes
   - Verify only one sync runs (no double-syncing or queued requests)

5. **Edge cases:**
   - Sync all with zero projects (status message should handle gracefully, e.g., "No projects to sync")
   - Sync all when all projects fail (status message shows all failures)
   - Sync all when multiple syncs happen rapidly (e.g., click, wait 1s, click again) — verify second click works

## Performance Considerations

- **Concurrency:** Sync all projects in parallel using `Promise.allSettled()`, not sequentially. Expected total time for N projects ≈ time for slowest single project + overhead, not N × time per project.
- **Network load:** Up to 10 concurrent requests (if there are 10 projects) — acceptable for localhost dashboard. If projects are remote, adjust based on network capacity.
- **DOM updates:** Each project's update is isolated to its own article element. No full re-render needed. Should be snappy even with 10+ projects.

## Migration Notes

None. This is a pure frontend addition with no data model changes or migrations.

## References

- S-06 plan: `context/archive/2026-07-23-manual-single-project-sync/plan.md` (per-project refresh pattern)
- S-08 plan: autosync interval configuration (uses same state management patterns)
- PRD: `context/foundation/prd.md` (FR-007 requirement for sync all)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Frontend HTML & Global State

#### Automated

- [x] 1.1 HTML validates without errors — bddffd6
- [x] 1.2 No JavaScript syntax errors in app.js — bddffd6

#### Manual

- [ ] 1.3 "Sync All" button visible at top of dashboard
- [ ] 1.4 Status message area present below button

### Phase 2: Core Sync Logic

#### Automated

- [x] 2.1 No JavaScript syntax errors after modifications
- [x] 2.2 Existing functionality still works (per-project refresh still functions)

#### Manual

- [ ] 2.3 Click "Sync All"; button disables and individual buttons disable
- [ ] 2.4 All projects sync concurrently (multiple updates appear quickly)
- [ ] 2.5 Status message shows after sync completes ("Synced X/Y projects")
- [ ] 2.6 Button and individual buttons re-enable after sync completes
- [ ] 2.7 Partial failure handling: one project fails, others succeed, summary shown

### Phase 3: UI Styling & Polishing

#### Automated

- [ ] 3.1 CSS parses without errors

#### Manual

- [ ] 3.2 Button and status message visually consistent with existing controls
- [ ] 3.3 Status message readable and properly styled
- [ ] 3.4 Responsive design: elements visible and usable on smaller screens
