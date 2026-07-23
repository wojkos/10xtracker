# Configure Autosync Interval Implementation Plan

## Overview

Add a small control to the dashboard letting the user enable/disable automatic background refresh and set how often it runs (in minutes). No new "sync all" backend endpoint is introduced — the frontend timer reuses the existing per-project `syncProject()` function (already shipped in S-06) across every currently-tracked project. The interval and enabled/disabled state persist server-side in a new `data/settings.json`, following the exact load/save pattern already established by `app/projects.py`.

## Current State Analysis

- `GET /api/projects` (`app/api.py:42-44`) already performs a full, stateless re-read of every tracked project from disk on every call (`app/changes.py:60-73`) — there is no caching layer to invalidate.
- Manual per-project sync (S-06, done) already exists: a "Refresh" button per project calls `syncProject(projectPath)` in `dist/app.js:156-231`, which fetches `/api/projects`, finds the matching project client-side, and patches only that project's DOM subtree (stats + changes list), showing errors in a per-project `#sync-error-{path}` div. This function already has its own try/catch/finally and per-project loading-state tracking (`loadingProjects` Set).
- S-07 ("sync-all-projects"), listed in the roadmap as this change's prerequisite, does **not** exist in code — no dedicated sync-all endpoint or button. The roadmap's "proposed" status for S-07 is accurate, not stale.
- No app-wide settings/config storage exists yet. The only persisted state is `data/tracked_projects.json`, a bare JSON array of path strings managed by `app/projects.py` (`DATA_FILE`, `load_tracked_projects`, `save_tracked_projects`).
- No scheduler library is installed (`pyproject.toml` deps: `fastapi`, `pyyaml`, `uvicorn` only) — autosync will be a frontend `setInterval`-driven loop, not a backend background task.
- Frontend is plain vanilla JS/HTML/CSS with no framework or build step, served via FastAPI's `app.frontend("/", directory="dist")` (`app/main.py:7`). All JS lives in one file, `dist/app.js` (337 lines), no inline scripts.

### Key Discoveries:

- Because `syncProject()` already isolates loading state and errors per project, looping it across all tracked project paths achieves "sync all" behavior without any new backend route — this resolves the S-07 dependency gap without expanding this change's scope.
- `renderProjectSection()` (`dist/app.js:43-143`) always creates a `.sync-error` div per project (line 122-125) and stamps `data-project-path` on the project's `<article>` (line 45), so the autosync loop can discover which paths are currently rendered by querying the DOM rather than needing a second source of truth.
- `app/projects.py`'s pattern (module-level `DATA_FILE` constant, plain `load_*`/`save_*` functions, no classes, `mkdir(parents=True, exist_ok=True)` before write) is the established convention to mirror for the new settings storage.
- `tests/test_projects.py` and `tests/test_api.py` isolate `DATA_FILE` via `monkeypatch.setattr` in an autouse fixture — the same pattern applies to a new `settings.DATA_FILE`.

## Desired End State

A developer viewing the dashboard sees an autosync control (checkbox + interval-in-minutes number input) near the top of the page. Toggling the checkbox or changing the interval immediately persists the new setting server-side and starts/stops/reschedules a background timer. While enabled, every N minutes the app re-syncs all currently-tracked projects using the same per-project mechanism as the manual "Refresh" button — each project's stats and changes list update in place, and any individual project's sync failure shows inline in that project's error area without disrupting the others or stopping the timer. Reloading the page restores the last-saved enabled/interval setting and resumes autosync automatically if it was enabled.

**Verification**: Run the app, enable autosync with a 1-minute interval, wait just over a minute without touching the page, and confirm the project list refreshes automatically (visible via a manually-edited `change.md` picking up the change without clicking "Refresh"). Reload the page and confirm the checkbox and interval value are restored from the last save.

## What We're NOT Doing

- No dedicated `POST /api/sync-all` (or similar) backend endpoint — autosync reuses the existing per-project `syncProject()` loop instead.
- No backend scheduler (APScheduler, FastAPI `BackgroundTasks`, cron) — autosync is a frontend `setInterval` loop only; it only runs while the dashboard tab is open.
- No retry/backoff logic on sync failure — a failed project sync shows its existing inline error and the timer simply tries again next interval (same behavior as leaving a broken project alone between manual refreshes).
- No per-project autosync interval — one global enabled/interval setting for the whole app.
- No multi-tab/multi-client coordination — if the dashboard is open in two tabs, each runs its own independent timer.

## Implementation Approach

Backend: add a new `app/settings.py` module mirroring `app/projects.py`'s exact shape (module-level `DATA_FILE`, plain `load_autosync_settings()` / `save_autosync_settings()` functions, JSON file with `mkdir(parents=True, exist_ok=True)`), plus `GET /api/settings` and `PUT /api/settings` routes in `app/api.py` with Pydantic request/response models following the existing `ProjectResponse`/`AddProjectRequest` style. `save_autosync_settings()` validates the interval is within `[1, 1440]` minutes and raises `ValueError` on violation, mirroring how `app/projects.py` raises `ValueError` for invalid state (caught in `api.py` and turned into HTTP 400).

Frontend: add a checkbox + number input to `dist/index.html` between the `<h1>` and the `#projects` container. On page load, fetch current settings and populate the controls, then start the timer if enabled. On any control change, validate client-side, `PUT` the new settings, and reschedule the timer. The timer's tick handler queries the DOM for all currently-rendered `article[data-project-path]` elements and calls the existing `syncProject(path)` for each — no new sync logic, just orchestration of what's already there.

## Phase 1: Backend — Autosync Settings Persistence & API

### Overview

Add settings storage and the two API routes needed to read and update the autosync enabled/interval state.

### Changes Required:

#### 1. `app/settings.py` (new file)

**Intent**: Persist the autosync enabled flag and interval (minutes) to disk, following `app/projects.py`'s established load/save pattern exactly, including validation of the interval bounds.

**Contract**: `DATA_FILE = Path("data/settings.json")`. `DEFAULT_INTERVAL_MINUTES = 5`, `MIN_INTERVAL_MINUTES = 1`, `MAX_INTERVAL_MINUTES = 1440`. `load_autosync_settings() -> tuple[bool, int]` returns `(enabled, interval_minutes)`, defaulting to `(False, DEFAULT_INTERVAL_MINUTES)` when `DATA_FILE` doesn't exist. `save_autosync_settings(enabled: bool, interval_minutes: int) -> None` raises `ValueError` if `interval_minutes` is outside `[MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES]`, otherwise writes `{"enabled": ..., "interval_minutes": ...}` as JSON, creating the parent directory first.

#### 2. `app/api.py`

**Intent**: Expose the settings as a small JSON API so the frontend can read the current autosync configuration on load and persist changes when the user edits it.

**Contract**: Add `SettingsResponse(BaseModel)` with fields `enabled: bool`, `interval_minutes: int`. Add `UpdateSettingsRequest(BaseModel)` with the same two fields. Add `GET /settings` returning the current `SettingsResponse` via `load_autosync_settings()`. Add `PUT /settings` accepting `UpdateSettingsRequest`, calling `save_autosync_settings(...)`, catching `ValueError` and raising `HTTPException(status_code=400, detail=str(exc))` (same pattern as `add_project`), and returning the saved `SettingsResponse` on success.

#### 3. `tests/test_settings.py` (new file)

**Intent**: Cover the new persistence module's load/save/validation behavior in isolation, mirroring `tests/test_projects.py`'s structure (autouse fixture monkeypatching `DATA_FILE` to a tmp path).

**Contract**: Tests for: default return value when no file exists, save-then-load round trip, rejecting an interval below `MIN_INTERVAL_MINUTES`, rejecting an interval above `MAX_INTERVAL_MINUTES`.

#### 4. `tests/test_api.py`

**Intent**: Cover the two new routes end-to-end through the FastAPI `TestClient`, mirroring the existing project-route tests in the same file.

**Contract**: Add an autouse fixture isolating `settings.DATA_FILE` to a tmp path (alongside the existing `projects.DATA_FILE` fixture). Tests for: `GET /api/settings` returns defaults when nothing saved yet, `PUT /api/settings` with a valid payload returns 200 and the saved values, a subsequent `GET /api/settings` reflects the update, and `PUT /api/settings` with an out-of-range `interval_minutes` returns 400 with a `detail` field.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_settings.py` passes
- [ ] `uv run pytest tests/test_api.py` passes
- [ ] `uv run pytest` passes (full suite, no regressions)
- [ ] `uv run python -c "import app.main"` succeeds

#### Manual Verification:

- [ ] `curl -X GET http://127.0.0.1:8000/api/settings` returns `{"enabled": false, "interval_minutes": 5}` on a fresh install
- [ ] `curl -X PUT http://127.0.0.1:8000/api/settings -H "Content-Type: application/json" -d "{\"enabled\": true, \"interval_minutes\": 10}"` returns 200 with the updated values, and a follow-up GET reflects them

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Frontend — Autosync Controls & Timer

### Overview

Add the enable/interval UI controls, wire them to the new settings API, and drive a client-side timer that re-syncs every tracked project using the existing `syncProject()` function.

### Changes Required:

#### 1. `dist/index.html`

**Intent**: Add the autosync checkbox and interval input near the top of the page, close to the project list, plus an inline error area for invalid input or save failures.

**Contract**: Insert a control block between the `<h1>` and `<div id="projects">`: a checkbox `#autosync-enabled` with a label, a `number` input `#autosync-interval` (`min="1" max="1440"`), and a `<span id="autosync-error" role="alert">` for validation/save errors.

#### 2. `dist/app.js`

**Intent**: Load the saved autosync settings on page start, populate the controls, start the timer if enabled, and persist + reschedule whenever the user changes either control. The timer's tick reuses the existing per-project sync rather than introducing new sync logic.

**Contract**:
- Add a module-level `let autosyncTimerId = null;`.
- Add `async function loadAutosyncSettings()`: `fetch("/api/settings")`, populate `#autosync-enabled` (checked) and `#autosync-interval` (value) from the response, then call `scheduleAutosync(enabled, interval_minutes)`.
- Add `async function saveAutosyncSettings(enabled, intervalMinutes)`: `PUT /api/settings` with `{enabled, interval_minutes: intervalMinutes}`; on non-2xx, show `body.detail` in `#autosync-error` and leave the timer unchanged; on success, clear the error and call `scheduleAutosync(enabled, intervalMinutes)`.
- Add `function scheduleAutosync(enabled, intervalMinutes)`: `clearInterval(autosyncTimerId)` if set; if `enabled`, `autosyncTimerId = setInterval(autosyncAll, intervalMinutes * 60 * 1000)`.
- Add `async function autosyncAll()`: reads all currently-rendered project paths via `document.querySelectorAll("article[data-project-path]")`, then `await`s `syncProject(path)` sequentially for each (reuses the existing function unmodified — no new sync/error-handling code).
- Wire `change` event listeners on `#autosync-enabled` and `#autosync-interval`: on change, validate the interval client-side (integer within `1`–`1440`; out-of-range shows an inline error in `#autosync-error` and skips the save), then call `saveAutosyncSettings(...)` with the current checkbox/input values.
- In the `DOMContentLoaded` handler, call `loadAutosyncSettings()` after the existing `loadProjects()`/`applyExpandedState()` calls.

#### 3. `dist/style.css`

**Intent**: Give the new control block minimal styling consistent with the existing form/button visual language (spacing, border, error text color).

**Contract**: A `#autosync-controls` rule for layout (flex row, gap, margin) and reuse of the existing `--text-error` variable for `#autosync-error`, matching `#add-project-error`'s existing styling approach.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run python -c "import app.main"` succeeds (no backend regression)
- [ ] `curl http://127.0.0.1:8000/` returns HTTP 200 with the updated HTML

#### Manual Verification:

- [ ] Browser: Load the dashboard, confirm the autosync checkbox is unchecked and interval shows `5` on a fresh install
- [ ] Browser: Check the box, confirm a `PUT /api/settings` fires (network tab) and succeeds
- [ ] Browser: Set interval to `1`, enable autosync, edit a tracked project's `change.md` status outside the app, wait ~60-90 seconds without touching the page, confirm the dashboard updates automatically without clicking "Refresh"
- [ ] Browser: While autosync is running, rename one tracked project's directory to break its path, confirm that project's inline error appears on the next tick while other projects keep updating normally and the timer keeps running
- [ ] Browser: Reload the page, confirm the checkbox and interval value reflect the last saved settings and autosync resumes automatically if it was enabled
- [ ] Browser: Enter an out-of-range interval (e.g. `0` or `2000`), confirm an inline error appears and no request that would corrupt `settings.json` succeeds

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- `app/settings.py` load/save/validation, isolated via `tmp_path` monkeypatching (mirrors `tests/test_projects.py`).

### Integration Tests:

- `GET`/`PUT /api/settings` end-to-end through FastAPI's `TestClient` (mirrors `tests/test_api.py`).

### Manual Testing Steps:

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/`, add a tracked project.
3. Confirm the autosync checkbox/interval default to unchecked / `5`.
4. Set the interval to `1`, enable autosync.
5. Outside the app, edit that project's `change.md` (change `status`).
6. Wait ~60-90 seconds without interacting with the page; confirm the change appears automatically.
7. Break a project's path (rename its directory) and confirm only that project shows an inline error on the next autosync tick; the timer keeps running and other projects keep updating.
8. Reload the page; confirm the checkbox/interval reflect the last save and autosync resumes if it was enabled.
9. Try an invalid interval (`0`, `2000`) and confirm it's rejected with an inline error, not silently saved.

## Performance Considerations

Autosync reuses the existing per-project `syncProject()` fetch, sequentially per tracked project on each tick — at v1 scale (1-10 projects per PRD), a tick completes well within a second on typical local I/O. No additional backend load beyond what manual "Refresh" already generates; the only difference is the trigger being a timer instead of a click.

## Migration Notes

Purely additive. `data/settings.json` doesn't exist until the first save; `load_autosync_settings()` returns sensible defaults (`enabled=False`, `interval_minutes=5`) until then. No changes to `data/tracked_projects.json` or its schema.

## References

- Roadmap: `context/foundation/roadmap.md` (S-08: Configure autosync interval)
- PRD: `context/foundation/prd.md` (FR-008)
- S-06 plan (manual sync mechanism being reused): `context/archive/2026-07-23-manual-single-project-sync/plan.md`
- Settings storage pattern to mirror: `app/projects.py:1-49`
- Existing sync mechanism being reused: `dist/app.js:156-231` (`syncProject`)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Backend — Autosync Settings Persistence & API

#### Automated

- [x] 1.1 `uv run pytest tests/test_settings.py` passes — ee01607
- [x] 1.2 `uv run pytest tests/test_api.py` passes — ee01607
- [x] 1.3 `uv run pytest` passes (full suite, no regressions) — ee01607
- [x] 1.4 `uv run python -c "import app.main"` succeeds — ee01607

#### Manual

- [ ] 1.5 `GET /api/settings` returns defaults on a fresh install
- [ ] 1.6 `PUT /api/settings` saves and a follow-up GET reflects the update

### Phase 2: Frontend — Autosync Controls & Timer

#### Automated

- [ ] 2.1 `uv run python -c "import app.main"` succeeds
- [ ] 2.2 `curl http://127.0.0.1:8000/` returns HTTP 200

#### Manual

- [ ] 2.3 Browser: Checkbox/interval default to unchecked / `5` on fresh install
- [ ] 2.4 Browser: Checking the box triggers and succeeds a settings save
- [ ] 2.5 Browser: 1-minute autosync picks up an external `change.md` edit without manual refresh
- [ ] 2.6 Browser: A broken project shows inline error on autosync tick; others keep updating, timer keeps running
- [ ] 2.7 Browser: Reload restores last-saved settings and resumes autosync if enabled
- [ ] 2.8 Browser: Out-of-range interval is rejected with inline error
