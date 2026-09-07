# Archive/Deactivate Inactive Projects Implementation Plan

## Overview

Add a per-project `active` flag to the tracked-projects list so the user can mark a project inactive (no filesystem scanning, no dashboard clutter) without losing it entirely, and reactivate it later. This directly addresses the original request: *"there is no point to scan their folders... block/archive as the other option then remove... maybe next week I will back to work."*

## Current State Analysis

- `data/tracked_projects.json` is a flat JSON array of path strings. `app/projects.py` has no per-project metadata slot at all — a tracked project is just a `pathlib.Path` ([app/projects.py:13-24](app/projects.py#L13-L24)).
- Every scan-triggering surface (manual refresh, sync-all, the client-side autosync timer, `/api/recommendations`, `get_recent_work`, and the MCP `get_project_status`/`get_next_10x_action` tools) converges on exactly one function: `get_project_statuses()` ([app/project_status.py:27-29](app/project_status.py#L27-L29)).
- No server-side scheduler or cache exists — every "sync" action is just a fresh `GET /api/projects`, so filtering at the choke point covers autosync automatically.
- `dist/` is hand-written vanilla JS/CSS, no build step. `renderProjectSection()` ([dist/app.js:114-196](dist/app.js#L114-L196)) renders each card; `.project-controls` ([dist/app.js:133-160](dist/app.js#L133-L160)) already holds Refresh and Remove buttons. `syncAllProjects`/`autosyncAll` discover projects to sync by querying `article[data-project-path]` in the DOM ([dist/app.js:274](dist/app.js#L274), [dist/app.js:492](dist/app.js#L492)).
- The "Add project" form sits directly below the `#projects` container in [dist/index.html:39-45](dist/index.html#L39-L45).
- `context/foundation/roadmap.md:197` parks "Archive actions from the UI" citing the PRD Non-Goal "Not an orchestration tool" ([context/foundation/prd.md:111](context/foundation/prd.md#L111)) and lists it as v2+ in Secondary Success Criteria ([context/foundation/prd.md:42](context/foundation/prd.md#L42)).

## Desired End State

A tracked project can be toggled inactive from its card. Inactive projects:
- Are excluded from all scanning (manual refresh, sync-all, autosync, recommendations, MCP tools) via the existing `get_project_statuses()` choke point.
- Disappear from the main project list and from summary/aggregate stats.
- Appear in a new "Archived Projects" section below the Add Project form, showing only name and path (no scan data), with an "Unarchive" action.

**Verification**: add two projects, archive one — it vanishes from the main list and stats, appears in the Archived section, and a page reload preserves the state (backed by `tracked_projects.json`). Unarchiving restores it to the main list and resumes scanning.

### Key Discoveries:

- `get_project_statuses()` is the single correct choke point for skipping scans — filtering there (not in `load_tracked_projects()`, which add/remove logic also needs, and not in `get_project_status()`, which the add-project flow calls directly on a fresh path) covers every read path in the app with one guard clause.
- The codebase's persistence convention is a module-level `DATA_FILE` constant plus plain `load_*`/`save_*` functions, no ORM/classes (mirrored identically in `app/projects.py` and `app/settings.py`). The migrated schema should follow this shape.
- `syncAllProjects`/`autosyncAll` select sync targets via `document.querySelectorAll("article[data-project-path]")` — the new Archived section must NOT use that attribute on its elements, or archived (unscanned) projects would get swept into bulk sync calls.

## What We're NOT Doing

- Not adding a separate "block" state distinct from "archive" — one boolean `active` flag covers the user's stated need (confirmed as in-scope during questioning).
- Not persisting or displaying last-known scan data (changes/status) for archived projects — the Archived section shows name/path only.
- Not adding a bulk archive/unarchive action — only per-project toggles.
- Not touching MCP tools (`app/mcp.py`) — they reuse `get_project_statuses()`/`get_project_status()` and pick up the active-only filtering automatically, with no MCP-specific changes needed.
- Not building a data migration script — the schema change is handled by lazy migrate-on-read.
- Not reversing the "Not an orchestration tool" non-goal for actions the app takes *on a tracked project's own files* (e.g., archiving a change, editing files) — those remain out of scope. This plan's "active" flag is purely internal dashboard state, not a filesystem mutation of the tracked project.

## Implementation Approach

Follow the codebase's existing plain-function persistence pattern. Represent a tracked entry as a small dataclass (`TrackedProject`, with `path: Path` and `active: bool`) rather than the current bare `Path`. `load_tracked_projects()` accepts both the legacy bare-string shape (treated as `active=True`) and the new object shape, and any subsequent `save_tracked_projects()` call rewrites the file in the new format — no separate migration step to run or forget. Filtering happens once, at the existing `get_project_statuses()` choke point. The frontend adds one button and one new page section, following the existing Refresh/Remove button and `removeProject()` fetch-then-reload patterns.

## Phase 1: Data Model & Persistence

### Overview

Migrate the tracked-projects storage to carry an `active` flag per project, with lazy migration from the legacy bare-path-string format, and add the toggle function other phases will call.

### Changes Required:

#### 1. Tracked-project storage and CRUD

**File**: `app/projects.py`

**Intent**: Represent each tracked project as `{path, active}` instead of a bare path, so the app can remember which projects are inactive. Existing legacy entries (bare strings) must load correctly as active, and any write normalizes the file to the new shape.

**Contract**: Introduce a `TrackedProject` dataclass with `path: Path` and `active: bool = True`. `load_tracked_projects() -> list[TrackedProject]` must accept both a bare string entry (legacy, `active=True`) and a `{"path": str, "active": bool}` entry within the same JSON array. `save_tracked_projects(entries: list[TrackedProject]) -> None` always writes the new object shape. `add_tracked_project(path)` appends a new `TrackedProject` with `active=True`. `remove_tracked_project(path)` filters entries by path as before (dedup/removal logic keys off `entry.path`, unchanged case-insensitive matching). Add `set_project_active(path: Path, active: bool) -> None`: resolves the path, raises `ValueError` if not tracked (mirroring `remove_tracked_project`'s not-found behavior), otherwise updates that entry's `active` field and saves.

#### 2. Persistence tests

**File**: `tests/test_projects.py`

**Intent**: Cover the new shape, the legacy-format migration path, and the new toggle function, alongside updating existing assertions that currently expect a bare `list[Path]`.

**Contract**: Update `test_save_then_load_round_trip` and other assertions to compare against `TrackedProject` entries (or their `.path`/`.active` fields) instead of bare `Path` objects. Add a test that seeds `DATA_FILE` with a legacy bare-string JSON array and asserts `load_tracked_projects()` returns entries with `active=True`. Add tests for `set_project_active`: toggling an existing tracked project's flag persists across a reload, and toggling an untracked path raises `ValueError`.

### Success Criteria:

#### Automated Verification:

- Unit tests pass: `uv run pytest tests/test_projects.py`

#### Manual Verification:

- None for this phase — no user-facing surface yet.

---

## Phase 2: Scan Pipeline & API Surface

### Overview

Wire the new `active` flag into the scan choke point so inactive projects are never scanned, and expose the toggle plus a lightweight inactive-projects listing over the API.

### Changes Required:

#### 1. Scan choke point

**File**: `app/project_status.py`

**Intent**: Skip scanning inactive projects everywhere `get_project_statuses()` is used (manual refresh, sync-all, autosync's `GET /api/projects`, recommendations, recent-work, MCP tools).

**Contract**: `get_project_statuses()` iterates only `entry for entry in load_tracked_projects() if entry.active`, calling `get_project_status(entry.path)` as before. `get_project_status()` itself is unchanged (still callable directly on any path, e.g. by the add-project flow). Add a lightweight `get_inactive_projects() -> list[ProjectSummary]` that reads `load_tracked_projects()`, filters to `not entry.active`, and returns `{path, name}` pairs without calling `list_changes()` — no scanning. Add a `ProjectSummary` Pydantic model (`path: str`, `name: str`) alongside the existing `ProjectResponse`.

#### 2. API endpoints

**File**: `app/api.py`

**Intent**: Let the frontend toggle a project's active state and fetch the archived list.

**Contract**: Add `PUT /api/projects/active` accepting `{path: str, active: bool}` (reuse or extend the existing request-model pattern at [app/api.py:14-16](app/api.py#L14-L16)), calling `set_project_active`, raising `HTTPException(404)` on `ValueError` (mirroring `remove_project`'s pattern at [app/api.py:42-48](app/api.py#L42-L48)), returning `{"active": bool}`. Add `GET /api/projects/inactive` returning `list[ProjectSummary]` via `get_inactive_projects()`.

#### 3. API tests

**File**: `tests/test_api.py`

**Intent**: Cover the new endpoints and confirm `GET /api/projects` excludes inactive projects.

**Contract**: Add tests: toggling a tracked project to inactive via `PUT /api/projects/active` removes it from a subsequent `GET /api/projects` response and makes it appear in `GET /api/projects/inactive`; toggling back to active reverses both; toggling an untracked path returns 404.

### Success Criteria:

#### Automated Verification:

- Unit tests pass: `uv run pytest tests/test_projects.py tests/test_api.py`
- Full test suite passes: `uv run pytest`

#### Manual Verification:

- None for this phase — verified end-to-end in Phase 3.

---

## Phase 3: Frontend UI

### Overview

Add the Archive action to each project card and a new "Archived Projects" section below the Add Project form, so the user can archive/unarchive without leaving the dashboard.

### Changes Required:

#### 1. Archive button on active project cards

**File**: `dist/app.js`

**Intent**: Let the user archive a project from its card, with a confirmation dialog (consistent with the existing Remove action), then refresh the dashboard so the card disappears from the main list.

**Contract**: In `renderProjectSection()`, add an "Archive" button to `.project-controls` after the existing Remove button ([dist/app.js:153-160](dist/app.js#L153-L160)). Its click handler calls `window.confirm(...)`, then on confirmation calls `PUT /api/projects/active` with `{path, active: false}`, then `loadProjects()` (main list) and `loadArchivedProjects()` (new function, see below) and `loadRecommendations()`, following the existing `removeProject()` pattern ([dist/app.js:330-360](dist/app.js#L330-L360)).

#### 2. Archived Projects section

**File**: `dist/app.js`, `dist/index.html`

**Intent**: Render inactive projects (name + path only) in a distinct section the user can browse and unarchive from, without triggering any scan.

**Contract**: Add `<div id="archived-projects"></div>` in `dist/index.html` directly below the existing Add Project form ([dist/index.html:44-45](dist/index.html#L44-L45)). Add `loadArchivedProjects()` (fetches `GET /api/projects/inactive`, renders into `#archived-projects`) and a render function producing one row per inactive project: name, path, and an "Unarchive" button. Unarchive has no confirmation dialog (non-destructive — it only resumes scanning) and calls `PUT /api/projects/active` with `{path, active: true}`, then refreshes both `loadProjects()` and `loadArchivedProjects()`. Elements in this section must NOT carry the `data-project-path` attribute on an `article` tag, so they are not swept up by `syncAllProjects`'s and `autosyncAll`'s `document.querySelectorAll("article[data-project-path]")` selectors ([dist/app.js:274](dist/app.js#L274), [dist/app.js:492](dist/app.js#L492)). Call `loadArchivedProjects()` once alongside the existing `loadProjects()` call in the `DOMContentLoaded` handler ([dist/app.js:553-564](dist/app.js#L553-L564)).

#### 3. Styling

**File**: `dist/style.css`

**Intent**: Give the Archive button and Archived Projects section a visual treatment consistent with the existing design system.

**Contract**: Add an `.archive-btn` rule following the `.remove-btn` precedent ([dist/style.css:61-73](dist/style.css#L61-L73)) for the Archive button, and `#archived-projects` styling (muted, compact rows) consistent with the app's existing card/section conventions.

### Success Criteria:

#### Automated Verification:

- Full test suite still passes (no backend regressions): `uv run pytest`

#### Manual Verification:

- Archiving a project (with confirmation) removes it from the main list and summary stats, and it appears in the Archived Projects section with only name/path.
- Unarchiving (no confirmation prompt) returns the project to the main list, resumes scanning, and removes it from the Archived section.
- A page reload after archiving preserves the archived state (data persisted in `tracked_projects.json`).
- Sync All and autosync do not attempt to refresh archived projects, and do not error because of their presence.
- Adding a brand-new project still works unaffected (new projects default to active).

---

## Phase 4: Docs Reconciliation

### Overview

Reconcile this feature with the PRD/roadmap, which previously parked "archive actions" as a non-goal, per the decision made during planning to proceed and update the docs.

### Changes Required:

#### 1. PRD update

**File**: `context/foundation/prd.md`

**Intent**: Clarify that the "Not an orchestration tool" non-goal ([context/foundation/prd.md:111](context/foundation/prd.md#L111)) refers to the app taking actions on a tracked project's own files (creating/archiving changes, updating status) — not to the app's own internal dashboard state (which project entries it chooses to scan). Remove "archive actions" from the v2+ Secondary Success Criteria list ([context/foundation/prd.md:42](context/foundation/prd.md#L42)) since the project-level active/inactive toggle is now a v1 feature, distinct from any future in-app change-archiving action.

**Contract**: Edit the Non-Goals bullet and the Secondary Success Criteria line to reflect this distinction. No new sections needed.

#### 2. Roadmap update

**File**: `context/foundation/roadmap.md`

**Intent**: Move the "Archive actions from the UI" Parked item's scope to explicitly cover only in-app orchestration of a tracked project's own files (e.g. archiving a change from the dashboard), and record the project-level active/inactive toggle as a new, now-delivered roadmap item.

**Contract**: Edit the Parked bullet at [context/foundation/roadmap.md:197](context/foundation/roadmap.md#L197) to narrow its wording, and add a new entry (e.g. under Done, once Phases 1-3 land) for this change, following the existing Done-list format ([context/foundation/roadmap.md:203-209](context/foundation/roadmap.md#L203-L209)).

### Success Criteria:

#### Automated Verification:

- None — documentation-only change.

#### Manual Verification:

- PRD Non-Goals and Secondary Success Criteria no longer contradict the shipped active/inactive feature.
- Roadmap Parked list and Done list accurately reflect the new feature and the still-parked in-app change-archiving action.

---

## Testing Strategy

### Unit Tests:

- Legacy bare-string entries load as `active=True`.
- New `{path, active}` entries round-trip through save/load unchanged.
- `set_project_active` persists the toggle and raises on an untracked path.
- `get_project_statuses()` excludes inactive projects; `get_inactive_projects()` returns only inactive ones without invoking `list_changes()`.

### Integration Tests:

- `PUT /api/projects/active` toggling in both directions, reflected in `GET /api/projects` and `GET /api/projects/inactive`.
- `PUT /api/projects/active` on an untracked path returns 404.

### Manual Testing Steps:

1. Add two projects; archive one via its card's Archive button (confirm dialog appears).
2. Verify the archived project disappears from the main list and its counts drop out of any aggregate/summary display.
3. Verify the archived project appears in the Archived Projects section with only name/path.
4. Reload the page; confirm the archived state persists.
5. Click Unarchive (no confirmation dialog); verify the project returns to the main list and begins scanning again.
6. Run Sync All while one project is archived; confirm no errors and the archived project isn't touched.

## Performance Considerations

None beyond current behavior — filtering is an O(n) list comprehension over an already-small tracked-project list (app targets 1-10 projects per the PRD's non-functional expectations).

## Migration Notes

No standalone migration script. `load_tracked_projects()` accepts the legacy bare-string shape at read time; the next `save_tracked_projects()` call (triggered by any add/remove/toggle) rewrites `data/tracked_projects.json` in the new `{path, active}` shape. Existing entries default to `active=True`, so no project silently disappears from the dashboard after this change ships.

## References

- Related research: `context/changes/archive-project/research.md`
- Choke point: [app/project_status.py:27-29](app/project_status.py#L27-L29)
- Persistence convention to mirror: [app/settings.py:4-28](app/settings.py#L4-L28)
- Existing Remove button/handler pattern: [dist/app.js:153-160](dist/app.js#L153-L160), [dist/app.js:330-360](dist/app.js#L330-L360)
- PRD Non-Goals: [context/foundation/prd.md:107-112](context/foundation/prd.md#L107-L112)
- Roadmap Parked list: [context/foundation/roadmap.md:194-201](context/foundation/roadmap.md#L194-L201)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Data Model & Persistence

#### Automated

- [x] 1.1 Unit tests pass: `uv run pytest tests/test_projects.py` — 355eaf1

### Phase 2: Scan Pipeline & API Surface

#### Automated

- [x] 2.1 Unit tests pass: `uv run pytest tests/test_projects.py tests/test_api.py`
- [x] 2.2 Full test suite passes: `uv run pytest`

### Phase 3: Frontend UI

#### Automated

- [ ] 3.1 Full test suite still passes (no backend regressions): `uv run pytest`

#### Manual

- [ ] 3.2 Archiving a project (with confirmation) removes it from the main list and summary stats, and it appears in the Archived Projects section with only name/path.
- [ ] 3.3 Unarchiving (no confirmation prompt) returns the project to the main list, resumes scanning, and removes it from the Archived section.
- [ ] 3.4 A page reload after archiving preserves the archived state (data persisted in `tracked_projects.json`).
- [ ] 3.5 Sync All and autosync do not attempt to refresh archived projects, and do not error because of their presence.
- [ ] 3.6 Adding a brand-new project still works unaffected (new projects default to active).

### Phase 4: Docs Reconciliation

#### Manual

- [ ] 4.1 PRD Non-Goals and Secondary Success Criteria no longer contradict the shipped active/inactive feature.
- [ ] 4.2 Roadmap Parked list and Done list accurately reflect the new feature and the still-parked in-app change-archiving action.
