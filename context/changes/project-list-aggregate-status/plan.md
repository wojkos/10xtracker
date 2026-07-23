# See Aggregated Status Counts Across All Tracked Projects — Implementation Plan

## Overview

Add a two-tier project dashboard to 10xDevTracker. The landing view shows a compact summary of all tracked projects with aggregate status counts (e.g., "2 New, 1 In Progress, 3 Done, 1 Blocked"). Clicking a project expands it to show its full change list (the current S-01 behavior). This is roadmap item **S-02** — the first aggregation view that justifies tracking multiple projects.

## Current State Analysis

- **S-01 status:** Phases 1 & 2 (backend) are complete; Phase 3 (frontend) is in progress with a basic form + change list rendering.
- **Current frontend** (`dist/app.js`) renders all projects' full change lists immediately on load, with no aggregation or summary view.
- **Current HTML** (`dist/index.html`) has a form to add projects and a container for rendering — no expand/collapse UI yet.
- **API is unchanged** — `GET /api/projects` still returns full per-change data; S-02 computes aggregates in JS rather than adding a new endpoint.
- **Status lifecycle** has 9 values (`new`, `preparing`, `planned`, `plan_reviewed`, `implementing`, `implemented`, `impl_reviewed`, `archived`, `blocked`) that map into three user-facing buckets.

## Desired End State

The developer opens the app and sees a compact project summary: one line per project showing `ProjectName (path)` with counts like "2 New, 1 In Progress, 3 Done" (with a note if any changes are blocked). Clicking a project expands it to show the full change list underneath (current S-01 detail view). Reloading the page preserves which projects were expanded. Adding a new project updates the summary list in-place.

**Verification**: Load the app with this repo as a tracked project (or add it), see aggregate counts render correctly (e.g., "1 New" for the current S-02 change, no In Progress, no Done since S-01 Phase 3 is still in progress). Click to expand and confirm individual changes appear. Reload the page and confirm expansion state persists.

### Key Discoveries:

- The status mapping is unambiguous: `new`/`preparing` → **New**, `planned`/`plan_reviewed`/`implementing` → **In Progress**, `implemented`/`impl_reviewed`/`archived` → **Done**, `blocked` → counted separately (shown as note if non-zero).
- Frontend-only aggregation keeps the API unchanged and defers the backend scaling concern to later slices (S-07 "sync all projects" will eventually benefit from a dedicated summary endpoint, but S-02 doesn't need it yet).
- Expand/collapse state via localStorage is 30–50 lines of JS; a simple JSON object keyed by `(path)` tracks which projects are open.

## What We're NOT Doing

- No API changes — aggregation is computed in JS from the existing `GET /api/projects` response.
- No unit tests for aggregation logic — the user opted for manual browser testing only; aggregation logic is simple arithmetic and best verified by human eyes on real data.
- No syncing or refresh UI — S-02 focuses only on the summary view presentation. Sync/autosync actions are S-06–S-08.
- No exporting or sharing of the dashboard — Non-Goal per PRD.
- No keyboard navigation or advanced accessibility features — base HTML semantics are sufficient for v1.

## Implementation Approach

Rebuild `dist/app.js` to:
1. Compute aggregate counts from each project's change list (status bucket mapping)
2. Render a two-tier view: summary first (collapsed), detail on expand
3. Wire expand/collapse to DOM state and localStorage

Keep HTML minimal — just update the structure to support summary rows and expandable details.

## Critical Implementation Details

**Status-to-bucket mapping:** Use this logic consistently in the aggregation function:
- `new`, `preparing` → **New**
- `planned`, `plan_reviewed`, `implementing` → **In Progress**
- `implemented`, `impl_reviewed`, `archived` → **Done**
- `blocked` → **Blocked** (counted separately, shown as a note if count > 0)

**Empty or all-error projects:** Show aggregate counts as "0 New, 0 In Progress, 0 Done" with a small inline note "(no readable changes)" to help the user understand the state without confusion.

**localStorage key scheme:** Store expanded state in `localStorage.expanded_projects` as a JSON object `{"/path/to/project": true, ...}` (one entry per expanded project; absence means collapsed). Load on page init; update on every expand/collapse toggle; load new additions immediately on form submission.

## Phase 1: Aggregation logic & data structures

### Overview

Add pure-JS functions to compute per-project aggregate counts from the change list. Prepare data structures for the two-tier view (summary + detail pairs).

### Changes Required:

#### 1. `dist/app.js`

**Intent**: Add aggregation logic and restructure the rendering to support both summary and detail views.

**Contract**: 
- New function `getStatusBucket(status: string): 'new' | 'in_progress' | 'done' | 'blocked'` — maps a single change's status to its bucket.
- New function `getAggregates(changes: array): {new: number, in_progress: number, done: number, blocked: number}` — counts changes by bucket, returns object.
- Modify existing `renderProjects(projects)` to call `getAggregates()` per project and store the result alongside each project in the data structure passed to rendering functions.
- Aggregation is performed on every render (no caching); ensures real data is always shown.

### Success Criteria:

#### Manual Verification:

- [ ] Load app, add this repo as a project, observe summary shows correct aggregate counts (manual inspection of rendered counts vs actual change statuses)
- [ ] Verify edge case: `context/changes/bootstrap-verification/` (has no `change.md`, skipped by S-01) does not appear in the count or the detail list

---

## Phase 2: Summary view rendering

### Overview

Rebuild the HTML and rendering logic to show a compact summary per project (name + counts), hidden-by-default detail list underneath each, all non-interactive initially.

### Changes Required:

#### 1. `dist/index.html`

**Intent**: Update the project list container structure to support both summary and detail rows.

**Contract**: Replace the generic `<div id="projects"></div>` with a structured layout:
```html
<div id="projects">
  <!-- Each project renders as: -->
  <article data-project-path="...">
    <header>
      <h2>ProjectName (path)</h2>
      <p class="summary-stats">X New, Y In Progress, Z Done<span class="blocked-note"> (1 Blocked)</span></p>
    </header>
    <div class="details" hidden>
      <ul>
        <!-- change list renders here -->
      </ul>
    </div>
  </article>
</div>
```
Keep the form unchanged. Add minimal CSS classes for styling (`.summary-stats`, `.blocked-note`, `.details`); styling details left to manual review.

#### 2. `dist/app.js` — `renderProjects()` function

**Intent**: Render each project as a summary + hidden detail section (no interactivity yet; Phase 3 adds expand/collapse).

**Contract**: 
- For each project, render an `<article data-project-path="...">` with the structure above.
- Summary line shows: `ProjectName (path)` as `<h2>`, followed by `<p class="summary-stats">` with formatted counts.
- If `aggregates.blocked > 0`, append `<span class="blocked-note">` with "(N Blocked)".
- For empty projects (0 all counts), show `(no readable changes)` note after the counts.
- Detail section contains the same change `<ul>` from S-01 (individual changes with status, updated date, or error message).
- Detail sections are `hidden` by default (Phase 3 toggles visibility).

### Success Criteria:

#### Manual Verification:

- [ ] Load app, add a project, see summary line with correct aggregate counts rendered above the detail list
- [ ] Verify blocked count (if any) renders in the note — e.g., "(1 Blocked)"
- [ ] Verify empty project shows "(no readable changes)" note

---

## Phase 3: Expand/collapse & localStorage persistence

### Overview

Wire up expand/collapse behavior: clicking the summary header toggles detail visibility and persists the state to localStorage.

### Changes Required:

#### 1. `dist/app.js` — expand/collapse logic

**Intent**: Add state management for project expanded/collapsed state, hooked to localStorage.

**Contract**:
- New function `loadExpandedState(): {[path]: boolean}` — reads `localStorage.expanded_projects`, returns object of expanded projects (defaults to `{}`).
- New function `saveExpandedState(state)` — writes object to `localStorage.expanded_projects`.
- Each `<article>` element gets a click handler on the `<header>` that toggles the `hidden` attribute on the `.details` section and updates localStorage.
- On page load (`DOMContentLoaded`), call `loadExpandedState()` and apply it immediately: iterate each `<article data-project-path>`, look up in the loaded state object, and set `.details.hidden` accordingly.
- On form submission (adding a new project), apply the loaded state to the newly rendered projects (so a new project starts collapsed by default).

#### 2. `dist/app.js` — click handler wiring

**Intent**: Connect summary clicks to the expand/collapse logic.

**Contract**: 
- In `renderProjects()`, after rendering each `<article>`, attach a click handler to its `<header>` (or wrap it in a clickable button/div with role=button for a11y, but summary-as-link is fine for v1).
- Handler toggles the `.details` section's `hidden` attribute.
- Handler calls `saveExpandedState()` with the updated state.
- Debounce not needed (user clicks are infrequent); localStorage writes are fast enough.

### Success Criteria:

#### Manual Verification:

- [ ] Click a project summary to expand it; detail list appears
- [ ] Click again to collapse; detail list disappears
- [ ] Reload the page; previously-expanded projects are still expanded
- [ ] Add a new project; it starts collapsed by default
- [ ] Click new project to expand; reload and confirm it persists

---

## Testing Strategy

### Manual Testing Only (per user request)

1. Open `http://127.0.0.1:8000/` with a running server (`uv run uvicorn app.main:app --reload`).
2. Add this repo as a project (or another local 10xDEV project).
3. Observe the summary line with aggregate counts for each project.
4. Click a project summary to expand and confirm individual changes appear below.
5. Click again to collapse; confirm the detail list vanishes.
6. Reload the page; confirm expanded projects are still expanded.
7. Add a second project and confirm it renders with its own summary and starts collapsed.
8. Expand both projects, reload, and confirm both expansion states are preserved.

## Performance Considerations

None significant. JS aggregation over typical project counts (1–10 projects, 20–50 changes each) is microseconds. localStorage writes are synchronous but fast for this data size.

## Migration Notes

None — the new UI replaces the existing full-list view. No data migration or deployed state to handle.

## References

- Roadmap: `context/foundation/roadmap.md` (S-02: See aggregated status across all projects)
- PRD: `context/foundation/prd.md` (FR-002: aggregated status counts)
- S-01 plan: `context/changes/project-change-status-view/plan.md` (current frontend code basis)
- Status schema: `.claude/skills/10x-new/references/change-md.md` (9 status values and transitions)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Aggregation logic & data structures

#### Automated

- [x] 1.1 `dist/app.js`: `getStatusBucket()` function added — b85acc8
- [x] 1.2 `dist/app.js`: `getAggregates()` function added — b85acc8
- [x] 1.3 `dist/app.js`: `renderProjects()` calls aggregation per project — b85acc8

#### Manual

- [ ] 1.4 Load app, add project, see correct aggregate counts

### Phase 2: Summary view rendering

#### Automated

- [x] 2.1 `dist/index.html`: structure updated for summary + detail layout
- [x] 2.2 `dist/app.js`: `renderProjects()` renders summary lines with counts

#### Manual

- [ ] 2.3 Verify summary rendered with correct format (ProjectName, counts, blocked note)
- [ ] 2.4 Verify detail list (from S-01) still renders underneath (hidden by default)

### Phase 3: Expand/collapse & localStorage persistence

#### Automated

- [ ] 3.1 `dist/app.js`: `loadExpandedState()` and `saveExpandedState()` functions added
- [ ] 3.2 `dist/app.js`: click handlers wire expand/collapse behavior

#### Manual

- [ ] 3.3 Click summary to expand/collapse; detail section toggles
- [ ] 3.4 Reload page; expanded projects are still expanded
- [ ] 3.5 Add new project; it starts collapsed, can be expanded
