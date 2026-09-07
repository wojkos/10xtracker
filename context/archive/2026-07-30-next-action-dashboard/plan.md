# Next Action Dashboard Panel Implementation Plan

## Overview

Expose workflow recommendations in the web dashboard so users see the next suggested 10x command without relying on MCP tooling. This adds a REST endpoint and a dashboard panel that renders one recommendation per tracked project, including low-confidence blocking details.

## Current State Analysis

`get_next_10x_action()` is already implemented and stable but currently reachable only through MCP tooling.

The dashboard currently loads projects and sync state but has no recommendation surface:
- `app/api.py` serves projects/settings endpoints only.
- `dist/index.html` has controls, project list, and add-project form.
- `dist/app.js` loads and re-renders projects for initial load, add/remove, refresh, sync-all, and autosync workflows.

## Desired End State

The dashboard includes a prominent "Next action" panel that displays one recommendation per tracked project with:
- command (when available),
- reason,
- confidence badge,
- blocking question and candidates for low-confidence states.

The panel stays current by reloading recommendations on initial page load and after add/remove/sync/sync-all/autosync operations.

### Key Discoveries:

- Recommendation logic and model already exist in `app/workflow_recommendations.py:13` and `app/workflow_recommendations.py:134`.
- API response-model conventions are already established in `app/api.py:31` and tested in `tests/test_api.py`.
- Frontend refresh lifecycle integration points are centralized in `dist/app.js` (initial load, `syncProject`, `syncAllProjects`, add/remove handlers, `autosyncAll`).
- Frontend is plain static files served via `app.main` (`app/main.py:8`), so the feature is additive with no build-tool changes.

## What We're NOT Doing

- No changes to recommendation decision logic in `app/workflow_recommendations.py`.
- No command execution controls (run/copy buttons) in the panel.
- No persistence or caching of recommendations on backend or frontend.
- No filtering UX (per-project toggles/search) for recommendations.
- No schema/data migration.

## Implementation Approach

Use the existing recommendation engine as the source of truth and expose it via a single API endpoint returning typed Pydantic models. Then render a dashboard panel using existing vanilla JS patterns and keep it synchronized by wiring recommendation reloads into existing lifecycle events.

## Critical Implementation Details

Timing & lifecycle: recommendation refresh calls must be placed after operations that can change project/change state (`loadProjects`, add/remove, `syncProject`, `syncAllProjects`, `autosyncAll`) to avoid displaying stale next-step guidance.

User experience spec: low-confidence recommendations must remain visible and actionable by always rendering `blocking_question` and `candidates` when present, rather than hiding ambiguous states.

## Phase 1: Add Recommendations API Endpoint

### Overview

Expose recommendation data through REST with typed response models and API coverage mirroring existing endpoint test style.

### Changes Required:

#### 1. API route and imports

**File**: `app/api.py`

**Intent**: Add `GET /api/recommendations` so the dashboard can fetch recommendation data via HTTP.

**Contract**: Import `WorkflowRecommendation` and `get_next_10x_action` from `app.workflow_recommendations` and add a route returning `list[WorkflowRecommendation]` with `response_model=list[WorkflowRecommendation]`.

#### 2. API tests

**File**: `tests/test_api.py`

**Intent**: Validate endpoint contract and ensure payload shape is stable.

**Contract**: Add tests that seed fixture projects and assert `GET /api/recommendations` returns HTTP 200 with expected list entries, including both high-confidence and low-confidence cases.

### Success Criteria:

#### Automated Verification:

- `python -m uv run pytest tests/test_api.py -v` passes with new recommendations endpoint coverage.
- `python -m uv run python -c "import app.main"` succeeds (router remains valid).

#### Manual Verification:

- Open `/docs` and confirm `GET /api/recommendations` is present with correct schema.
- Execute `GET /api/recommendations` in `/docs` and confirm list payload includes expected fields (`command`, `reason`, `confidence`, `blocking_question`, `candidates`).

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 2: Add Next Action Panel Rendering

### Overview

Add dashboard markup and frontend render logic for one recommendation per project, including low-confidence details.

### Changes Required:

#### 1. Dashboard section

**File**: `dist/index.html`

**Intent**: Add a dedicated dashboard area for recommendation display.

**Contract**: Insert a `#next-action` section between dashboard controls and projects list with a child container `#next-action-content`.

#### 2. Recommendation loader and renderer

**File**: `dist/app.js`

**Intent**: Fetch and render recommendations in a compact, readable panel.

**Contract**: Add `loadRecommendations()` that calls `/api/recommendations`, clears/rebuilds `#next-action-content`, and renders per-project blocks containing:
- project path,
- confidence badge,
- reason,
- command (if present),
- blocking question and candidate list (if present).

Error state should show a non-crashing inline panel message while leaving the rest of dashboard functional.

#### 3. Panel styling

**File**: `dist/style.css`

**Intent**: Style the panel consistently with existing card-like dashboard surfaces.

**Contract**: Add styles for `#next-action` container and recommendation elements (`confidence` variants, command text block, blocking-question emphasis) using existing color tokens.

### Success Criteria:

#### Automated Verification:

- `python -m uv run python -c "import app.main"` succeeds.
- `python -m uv run pytest tests/test_api.py -v` still passes after frontend-related changes.

#### Manual Verification:

- Dashboard shows one recommendation entry per tracked project.
- High-confidence entries show command + reason clearly.
- Low-confidence entries show reason + blocking question + candidates.
- Recommendation panel fetch failure does not break project list rendering.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 3: Wire Recommendation Refresh Lifecycle

### Overview

Ensure recommendation data stays current by reloading after all user actions that mutate observable project/change state.

### Changes Required:

#### 1. Initial load and CRUD hooks

**File**: `dist/app.js`

**Intent**: Keep panel up-to-date after page load and project add/remove operations.

**Contract**: Call `loadRecommendations()` on initial load (after project load) and after successful add/remove flows.

#### 2. Sync hooks

**File**: `dist/app.js`

**Intent**: Keep panel aligned with refresh workflows without redundant reloads.

**Contract**: Do not hook `loadRecommendations()` inside `syncProject()` itself — it is
called once per project by both the batch flows below, so hooking there would fire the
recommendations fetch N times per batch action. Instead, trigger `loadRecommendations()`
only at these call sites:
- the per-project Refresh button's click handler, after its `syncProject` call resolves,
- `syncAllProjects` completion (after all per-project syncs settle),
- `autosyncAll` completion (after its sync loop finishes).

This mirrors the existing pattern where `syncAllProjects`/`autosyncAll` already keep
batch-level UI updates (status text, article reordering) out of `syncProject` itself.

### Success Criteria:

#### Automated Verification:

- `python -m uv run pytest tests/test_api.py -v` passes.
- `python -m uv run python -c "import app.main"` succeeds.

#### Manual Verification:

- On page load, recommendations render without needing manual action.
- After add/remove, recommendations update to reflect new state.
- After refresh/sync-all/autosync, recommendations reflect latest change status transitions.
- Existing sync controls continue to work (no regressions in refresh loading states or error messages).

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before concluding implementation. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Testing Strategy

### Unit Tests:

- Extend API tests for recommendations response shape and confidence-state coverage.

### Integration Tests:

- Validate endpoint through FastAPI `TestClient` with fixture projects representing common recommendation scenarios.

### Manual Testing Steps:

1. Run app and add at least one fixture project with active changes.
2. Confirm recommendation panel renders one entry per tracked project.
3. Trigger project refresh and sync-all actions; verify panel updates after each action.
4. Create/adjust fixture state to force low-confidence recommendation; verify blocking fields render.
5. Remove a project; verify recommendation list shrinks accordingly.

## Performance Considerations

Recommendation generation reads project metadata from disk; at current product scope (small tracked-project sets), on-demand fetch after lifecycle events is acceptable. If panel update latency becomes noticeable, future optimization can add debounce/coalescing around rapid sequential refresh calls.

## Migration Notes

None. This is additive API + UI behavior with no persisted schema changes.

## References

- Related research: `context/changes/next-action-dashboard/research.md`
- Recommendation logic: `app/workflow_recommendations.py:13`, `app/workflow_recommendations.py:134`
- API patterns: `app/api.py`, `tests/test_api.py`
- Frontend lifecycle hooks: `dist/app.js`
- Similar prior plans: `context/archive/2026-07-24-sync-all-projects/plan.md`, `context/archive/2026-07-23-manual-single-project-sync/plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Add Recommendations API Endpoint

#### Automated

- [x] 1.1 `python -m uv run pytest tests/test_api.py -v` passes with recommendations endpoint coverage — 92226e1
- [x] 1.2 `python -m uv run python -c "import app.main"` succeeds — 92226e1

#### Manual

- [ ] 1.3 `/docs` shows `GET /api/recommendations` with expected schema
- [ ] 1.4 `/docs` response includes expected recommendation fields for high- and low-confidence cases

### Phase 2: Add Next Action Panel Rendering

#### Automated

- [x] 2.1 `python -m uv run python -c "import app.main"` succeeds — 94548a2
- [x] 2.2 `python -m uv run pytest tests/test_api.py -v` remains green after frontend changes — 94548a2

#### Manual

- [ ] 2.3 Dashboard shows one recommendation entry per tracked project
- [ ] 2.4 High-confidence entries show command and reason clearly
- [ ] 2.5 Low-confidence recommendations show reason, blocking question, and candidates
- [ ] 2.6 Recommendation panel fetch failure is visible but non-breaking

### Phase 3: Wire Recommendation Refresh Lifecycle

#### Automated

- [x] 3.1 `python -m uv run pytest tests/test_api.py -v` passes — f12fad0
- [x] 3.2 `python -m uv run python -c "import app.main"` succeeds — f12fad0

#### Manual

- [ ] 3.3 Recommendations load on initial page render
- [ ] 3.4 Recommendations refresh after add/remove and project sync actions
- [ ] 3.5 Recommendations refresh after sync-all and autosync cycles
- [ ] 3.6 Existing refresh/sync UI behavior remains intact
