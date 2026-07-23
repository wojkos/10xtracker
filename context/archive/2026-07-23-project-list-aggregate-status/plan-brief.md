# See Aggregated Status Counts Across All Tracked Projects — Plan Brief

> Full plan: `context/changes/project-list-aggregate-status/plan.md`
> Related: `context/changes/project-change-status-view/plan.md` (S-01, prerequisite)

## What & Why

S-02 adds a compact project-list summary view: instead of showing every project's full change list immediately, the dashboard displays a one-liner per project with aggregate status counts (e.g., "2 New, 1 In Progress, 3 Done"). This is the aggregation value the app was built to deliver — developers can now see at a glance which projects have active work without scrolling through dozens of changes.

## Starting Point

S-01 (`project-change-status-view`) is complete through Phase 2 (backend API and parsing). The frontend currently renders all projects' full change lists on load. We have no aggregation logic, no summary view, and no expand/collapse UI yet.

## Desired End State

Developers see a clean dashboard: each tracked project shown as a summary (name + aggregate counts), initially collapsed. Clicking a project expands it to show its detailed change list (the current S-01 view). Expanded state persists across page reloads via localStorage. Adding a new project updates the dashboard in-place.

## Key Decisions Made

| Decision                       | Choice                            | Why (1 sentence)  | Source           |
| ------------------------------ | --------------------------------- | -------------------- | -------- |
| Status-to-bucket mapping       | new/preparing→New, planned/plan_reviewed/implementing→In Progress, implemented/impl_reviewed/archived→Done, blocked→separate | Maps to natural change lifecycle phases; blocked changes count separately to avoid clutter. | Plan |
| Aggregation layer              | Frontend-only (no API changes)    | Simplest implementation; backend scaling deferred to S-07; keeps API unchanged and reusable. | User choice |
| UI flow                         | Two-tier: summary (collapsed) → click to expand details | Cleaner information hierarchy; typical dashboard pattern; users focus on summary first. | User choice |
| Empty/error project handling   | Show "0 New, 0 In Progress, 0 Done" + "(no readable changes)" note | Consistent display; users understand why counts are empty without silent failure. | User choice |
| UI state persistence           | localStorage for expanded/collapsed projects | Restores user's view preferences on reload; minimal overhead (~30-50 lines). | User choice |

## Scope

**In scope:**
- Aggregation functions (status-to-bucket mapping, count logic)
- Summary view rendering (one line per project with counts)
- Expand/collapse interaction and localStorage persistence
- Manual testing via browser

**Out of scope:**
- API endpoint changes (S-07 will revisit if needed)
- Unit tests for aggregation (user opted for manual verification only)
- Keyboard navigation or advanced accessibility features
- Syncing or refresh actions (S-06+)
- Export or sharing features

## Architecture / Approach

Pure JavaScript refactor of `dist/app.js`:
1. Add aggregation functions (`getStatusBucket()`, `getAggregates()`) to bucket changes into new/in-progress/done/blocked categories
2. Restructure rendering to show summary first (counts + aggregate) and detail list hidden underneath
3. Wire expand/collapse handlers and localStorage to persist which projects are open

No backend changes. HTML structure updated minimally to support summary + detail pairs.

## Phases at a Glance

| Phase     | What it delivers       | Key risk                  |
| --------- | ---------------------- | ------------------------- |
| 1. Aggregation logic | Status bucket mapping and count computation | Correct bucket assignment per change status |
| 2. Summary view | Summary lines with counts, detail lists hidden | Correct count formatting and edge cases (blocked, empty) |
| 3. Expand/collapse | Click-to-toggle behavior, localStorage persistence | State synchronization between DOM and localStorage |

**Prerequisites:** S-01 backend (API + change parsing) complete; running server available
**Estimated effort:** ~2-3 hours; 3 phases, mostly frontend JS/DOM work

## Open Risks & Assumptions

- **Assumption**: localStorage is available and writable (true on all modern browsers, localhost environment)
- **Assumption**: 9-to-3 status mapping is correct (validated against change-md schema)

## Success Criteria (Summary)

- Summary view renders each project with correct aggregate counts
- Clicking a project expands/collapses the detail list
- Expanded state persists across page reloads
- Empty or all-error projects show clear notes, not confusing blank counts
