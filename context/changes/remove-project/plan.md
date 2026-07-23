# Remove a Project — Implementation Plan

## Overview

Let a developer untrack a previously-added project from 10xDevTracker. This is roadmap item **S-05** (`remove-project`, FR-009) — a small, standalone action layered on top of S-01's existing add/list functionality. Removing a project only forgets its tracked path; it never touches the project's own files on disk.

## Current State Analysis

- [app/projects.py](../../../app/projects.py) has `load_tracked_projects`, `save_tracked_projects`, and `add_tracked_project`, but no removal function.
- [app/api.py](../../../app/api.py) exposes `POST /api/projects` and `GET /api/projects`, but no `DELETE`.
- [dist/app.js](../../../dist/app.js) renders each tracked project as a `<section>` with a heading and a changes list ([dist/app.js:1-24](../../../dist/app.js)), but has no per-project action controls.
- Projects are identified only by their filesystem **path** — there is no separate ID field anywhere in the model, so removal must key off the same path string used by `add_tracked_project`.
- `project-change-status-view`'s plan explicitly scopes removal out: *"No project removal UI — that's S-05 (`remove-project`)"* ([context/changes/project-change-status-view/plan.md:34](../../project-change-status-view/plan.md)) — confirming no conflict with that in-progress change.

## Desired End State

A developer viewing the dashboard sees a "Remove" control next to each tracked project. Clicking it, after confirming, calls the backend to untrack that project and re-renders the list without it. Removing a path that somehow isn't tracked (e.g., stale UI state) surfaces a clear error instead of silently succeeding or crashing.

**Verification**: add two projects via the existing form, remove one via its "Remove" button (confirming the browser prompt), see it disappear from the list while the other remains; reload the page and confirm the removal persisted.

### Key Discoveries:

- `add_tracked_project` compares resolved absolute paths case-insensitively ([app/projects.py:31-33](../../../app/projects.py)) — removal must use the same resolved, case-insensitive comparison so a path added as `d:\foo` can be removed via `D:\Foo`.
- FastAPI route registration order relative to `app.frontend()` doesn't matter (established in S-01) — the new `DELETE /api/projects` route can be added to the existing router without any ordering concerns.

## What We're NOT Doing

- No project ID field or migration of the persisted data format — removal keys off path, matching how add/list already work.
- No "undo remove" — re-adding the same path is cheap and already supported by the existing add flow.
- No bulk/multi-select removal — one remove action per project, matching the smallest-slice scope of S-05.
- No styled confirmation modal — a native browser `confirm()` is sufficient for this MVP, consistent with the app's minimal vanilla-JS approach.

## Implementation Approach

Extend the existing three-layer structure from S-01 (persistence → API → frontend) with one new operation at each layer: `remove_tracked_project` in the persistence layer, `DELETE /api/projects` in the API layer, and a "Remove" button per rendered project in the frontend.

## Phase 1: Persistence layer

### Overview

Add the ability to remove a tracked path from the local JSON-backed list, isolated from HTTP concerns and unit-testable on its own.

### Changes Required:

#### 1. `app/projects.py`

**Intent**: Add a function to untrack a project path, matching `add_tracked_project`'s existing path-resolution and comparison behavior so add/remove stay symmetric.

**Contract**: `remove_tracked_project(path: Path) -> None` resolves the input path, loads the tracked list, and removes the entry whose resolved path matches case-insensitively (same comparison as `add_tracked_project`'s duplicate check at [app/projects.py:31-33](../../../app/projects.py)). Raises `ValueError` with a human-readable message if no matching entry is found. Persists the updated list via the existing `save_tracked_projects`.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_projects.py -v` passes — covers: removing a tracked path succeeds and it's absent from a subsequent load, removing an untracked path raises `ValueError`, removal is case-insensitive on the path comparison

---

## Phase 2: API layer

### Overview

Expose Phase 1's removal function as a `DELETE /api/projects` endpoint, matching the existing `POST`/`GET` contract shape.

### Changes Required:

#### 1. `app/api.py`

**Intent**: Add a `DELETE` route that untracks a project by path, returning a clear error when the path isn't currently tracked.

**Contract**: New `RemoveProjectRequest` Pydantic model with a `path: str` field, matching `AddProjectRequest`'s shape. `DELETE /api/projects` takes this as the request body; on success, returns 200 with an empty/`{"removed": true}` body; on a `ValueError` from `remove_tracked_project` (path not tracked), returns 404 with FastAPI's standard `{"detail": str}` shape (using 404 rather than 400 here, distinct from the add-project 400s, since the failure mode is "not found" not "invalid input").

#### 2. `tests/test_api.py`

**Intent**: Verify the HTTP contract end-to-end.

**Contract**: Covers: `DELETE` on a previously-`POST`ed path returns 200 and the project no longer appears in a subsequent `GET /api/projects`; `DELETE` on a path that was never added returns 404 with a `detail` message.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_api.py -v` passes
- [ ] `uv run python -c "import app.main"` succeeds (router wiring doesn't break app construction)

#### Manual Verification:

- [ ] Start `uv run uvicorn app.main:app --reload`, open `http://127.0.0.1:8000/docs`, confirm `DELETE /api/projects` appears with correct request/response schemas
- [ ] Using the `/docs` "Try it out" UI, `POST` this repo's own path, then `DELETE` it, then confirm `GET /api/projects` no longer includes it

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Frontend UI

### Overview

Add a "Remove" control to each rendered project, guarded by a confirmation prompt, wired to the new `DELETE` endpoint.

### Changes Required:

#### 1. `dist/app.js`

**Intent**: Give each rendered project a "Remove" button that, after user confirmation, calls the delete endpoint and refreshes the list.

**Contract**: In `renderProjects`, add a button to each project's `<section>` whose click handler calls `window.confirm(...)`; on confirm, `fetch('/api/projects', {method: 'DELETE', headers: {"Content-Type": "application/json"}, body: JSON.stringify({path: project.path})})`, then re-run `loadProjects()` on success. On a non-2xx response, surface the response's `detail` inline (reusing the existing `#add-project-error` element or an equivalent per-project error spot) without removing the project from view.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run python -c "import app.main"` succeeds (no backend regression from this phase)
- [ ] Background server boot + `curl` on `/` still returns HTTP 200

#### Manual Verification:

- [ ] Browser: add two projects, click "Remove" on one, confirm the browser prompt, see only the other project remain
- [ ] Browser: dismiss the confirm prompt (Cancel) and confirm the project is NOT removed
- [ ] Browser: reload the page and confirm the removal persisted

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- `app/projects.py`: remove a tracked path (present afterward: no), remove an untracked path raises `ValueError`, case-insensitive path matching on removal.

### Integration Tests:

- `tests/test_api.py`: `DELETE` after `POST` removes the project from `GET`; `DELETE` on a never-added path returns 404.

### Manual Testing Steps:

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/`, add two real local project paths.
3. Click "Remove" on one, confirm the browser prompt, see it disappear while the other remains.
4. Click "Remove" again and dismiss (Cancel) — confirm nothing changes.
5. Reload the page, confirm the removal persisted.
6. Open `/docs`, confirm `DELETE /api/projects` is documented correctly.

## Performance Considerations

None — a single JSON-file rewrite over the same handful of tracked projects (1–10 per the PRD's stated scale), no different from the existing add/list operations.

## Migration Notes

None — no data format change; removal operates on the same `data/tracked_projects.json` structure S-01 already writes.

## References

- Roadmap: `context/foundation/roadmap.md` (S-05: Remove a project)
- PRD: `context/foundation/prd.md` (FR-009)
- Prior plan (S-01): `context/changes/project-change-status-view/plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Persistence layer

#### Automated

- [ ] 1.1 `uv run pytest tests/test_projects.py -v` passes

### Phase 2: API layer

#### Automated

- [ ] 2.1 `uv run pytest tests/test_api.py -v` passes
- [ ] 2.2 `uv run python -c "import app.main"` succeeds

#### Manual

- [ ] 2.3 `/docs` shows `DELETE /api/projects` with correct schemas
- [ ] 2.4 `POST` then `DELETE` via `/docs` against this repo's own path, confirm `GET` no longer includes it

### Phase 3: Frontend UI

#### Automated

- [ ] 3.1 `uv run python -c "import app.main"` succeeds
- [ ] 3.2 Background server boot + `curl` on `/` returns HTTP 200

#### Manual

- [ ] 3.3 Browser: remove one of two projects, confirm prompt, see it disappear while the other remains
- [ ] 3.4 Browser: dismiss confirm prompt, project is NOT removed
- [ ] 3.5 Browser: reload persists the removal
