# Add a Project Path and See Per-Change Status — Implementation Plan

## Overview

Add the first real feature to 10xDevTracker: a developer can submit a local 10xDEV project path, the app validates and tracks it, reads its `context/changes/*/change.md` files, and shows each change's raw status. This is roadmap item **S-01** — the north-star slice that proves the app can correctly parse a `context/changes/` directory into an accurate per-change list, which every later slice (S-02 through S-08) builds on.

## Current State Analysis

- [app/main.py](../../../app/main.py) is a bare FastAPI instance mounting `dist/` as a static frontend via `app.frontend("/", directory="dist")` — no API routes, no persistence, no data-parsing logic exist yet.
- [dist/index.html](../../../dist/index.html) is a static branded placeholder with no form, no JS, no dynamic content.
- [pyproject.toml](../../../pyproject.toml) declares only `fastapi` and `uvicorn` — no YAML parser, no test tooling (`pytest`, `httpx`).
- No `.gitignore` exists anywhere in the repo.
- The `change.md` schema ([change-md.md](../../../.claude/skills/10x-new/references/change-md.md)) defines 9 possible `status` values (`new`, `preparing`, `planned`, `plan_reviewed`, `implementing`, `implemented`, `impl_reviewed`, `archived`, `blocked`) — richer than the PRD's illustrative "new/in-progress/done" framing.
- This repo's own `context/changes/` already exercises a real edge case: [context/changes/bootstrap-verification/](../../../context/changes/bootstrap-verification/) has no `change.md` at all (only a `verification.md`), so a parser that assumes every change folder has one will break on real data.
- The PRD's FR-001 says the developer provides "a project directory containing `context/`", but US-01's example path (`D:\trinity\trinity-core\context`) points at the `context/` directory itself — a genuine inconsistency, resolved below in favor of the more precise FR wording.

## Desired End State

A developer can open `http://127.0.0.1:8000/`, submit a project root path (a directory containing a `context/changes/` folder) via a form, and see that project's changes rendered with their raw `change.md` status strings. Adding an invalid path shows an inline error instead of crashing or silently failing. Reloading the page still shows previously-added projects (JSON-file persistence). No aggregation, bucketing, sync buttons, or removal UI — those are later roadmap slices.

**Verification**: run the app, add this repo's own path (or another local 10xDEV project) via the form, see its changes with correct statuses render; reload the page and confirm they persist; try an invalid path and see a clear inline error.

### Key Discoveries:

- FastAPI's path operations always take precedence over `app.frontend()`'s static mount regardless of registration order (established and confirmed in the F-01 plan), so `/api`-prefixed routes coexist safely with the `/` frontend mount without any ordering constraints.
- `context/changes/bootstrap-verification/` (this repo, real data) has no `change.md` — confirms the parser must skip change folders that lack one rather than erroring.
- FastAPI already bundles Pydantic v2 as a dependency, so request/response models need no new dependency beyond a YAML parser for `change.md` frontmatter.

## What We're NOT Doing

- No 3-bucket status aggregation (new/in-progress/done counts) — raw `change.md` status strings are shown as-is; bucketed counts are S-02's job (`project-list-aggregate-status`).
- No phase/task progress from `plan.md` — that's S-03 (`change-phase-progress`).
- No roadmap correlation — that's S-04 (`roadmap-correlation-view`).
- No project removal UI — that's S-05 (`remove-project`).
- No manual re-sync button or autosync timer — `GET /api/projects` always reads fresh from disk on every call, so there's nothing to "sync" yet; S-06/S-07/S-08 add the explicit refresh actions and interval config on top of this.
- No new frontend framework or build tooling — vanilla JS against a JSON API, per `tech-stack.md`'s stated intent to add a real JS/TS frontend later against the same API.
- No scanning of `context/archive/` — only `context/changes/` (in-flight changes) is read, matching the PRD's Business Logic "Inputs" list.

## Implementation Approach

Build bottom-up: a pure-Python parsing/persistence layer first (unit-testable, no HTTP), then a thin FastAPI JSON layer on top of it (`/api` prefix, integration-tested with `TestClient`), then a small vanilla-JS addition to the existing static page that calls those two endpoints. Each layer only depends on the one below it, so phases can be verified independently before moving on.

## Critical Implementation Details

**Frontmatter extraction**: `change.md` is Markdown with a leading YAML frontmatter block delimited by `---` lines, not a pure YAML file — the parser must split on the two `---` delimiters and feed only the middle block to the YAML parser. A file missing the closing delimiter should be treated as a parse error on that one file, not raise an unhandled exception.

**Per-folder failure isolation**: one project's read must isolate failures per change-folder. A single malformed or partially-invalid `change.md` should surface as one error-flagged entry within that project's `changes` list — it must not fail the whole `GET /api/projects` response or block other tracked projects (or other changes in the same project) from loading correctly.

## Phase 1: Parsing & persistence layer

### Overview

Pure-Python logic: validate a candidate project path, parse a project's `context/changes/*/change.md` files into change summaries (tolerating missing/malformed files), and persist the tracked project path list to a local JSON file. No HTTP surface in this phase — fully unit-testable.

### Changes Required:

#### 1. `pyproject.toml`

**Intent**: Add the YAML parser needed for `change.md` frontmatter, and dev-only test tooling (`pytest`, `httpx` for FastAPI's `TestClient`) — deferred from the F-01 scaffold specifically until real logic existed worth testing.

**Contract**: `pyyaml` added as a runtime dependency (`uv add pyyaml`); `pytest` and `httpx` added as dev dependencies (`uv add --dev pytest httpx`).

#### 2. `.gitignore` (new, repo root)

**Intent**: The repo currently has no `.gitignore`; this change introduces the first files that genuinely shouldn't be committed (bytecode caches, and the new local project-tracking data file).

**Contract**: Ignores `__pycache__/`, `*.pyc`, `.venv/`, and the tracked-projects data path from item 4 below (`data/`).

#### 3. `app/changes.py` (new)

**Intent**: Parse a project's `context/changes/` directory into a list of change summaries, isolating per-folder failures so one bad file doesn't break the whole read.

**Contract**: Exposes `list_changes(context_dir: Path) -> list[ChangeSummary]`, where `ChangeSummary` (Pydantic model) has `change_id: str`, `title: str`, `status: str`, `updated: str`, and `error: str | None`. Folders with no `change.md` are skipped entirely (not a "change" per the framework's own definition — confirmed by this repo's `bootstrap-verification` folder). Folders whose `change.md` exists but fails to parse or is missing a required field are included with `error` set and the other fields best-effort/empty, so the caller can still show *something* went wrong for that specific change rather than losing it silently.

#### 4. `app/projects.py` (new)

**Intent**: Validate a candidate project path and read/write the local JSON-backed list of tracked project paths.

**Contract**: `validate_project_path(path: Path) -> Path` raises `ValueError` (with a human-readable message) when `<path>/context/changes` doesn't exist — this is the FR-001 interpretation ("directory containing `context/`"), treated as authoritative over US-01's example path which points at `context/` itself. `load_tracked_projects() -> list[Path]` and `save_tracked_projects(paths: list[Path]) -> None` read/write `data/tracked_projects.json` (parent directory created on first write if absent). `add_tracked_project(path: Path) -> Path` rejects a path that's already tracked, comparing resolved absolute paths case-insensitively (Windows paths).

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_changes.py -v` passes — covers: valid `change.md`, malformed YAML, missing required field, folder with no `change.md` (skipped)
- [ ] `uv run pytest tests/test_projects.py -v` passes — covers: valid path accepted, path without `context/changes` rejected, duplicate path rejected, save-then-load round-trip returns the same paths

---

## Phase 2: API layer

### Overview

Expose the Phase 1 logic over HTTP as two JSON endpoints under an `/api` prefix, kept deliberately separate from the `/` frontend mount.

### Changes Required:

#### 1. `app/api.py` (new)

**Intent**: Define the two JSON endpoints backed by the Phase 1 data layer, returning a consistent per-project shape both endpoints share.

**Contract**: `APIRouter` with two routes. `POST /api/projects` — body `{"path": str}`; on success, 200 with `{"path": str, "name": str, "changes": [ChangeSummary, ...]}` (`name` derived from the path's last folder segment); on invalid or duplicate path, 400 with FastAPI's standard `{"detail": str}` error shape (the `ValueError` message from `validate_project_path`/`add_tracked_project`). `GET /api/projects` — 200 with a list of that same per-project shape for every currently tracked project, recomputed fresh from disk on every call (no caching layer — keeps this read-only and leaves "sync" as a distinct future action rather than something GET has to fake).

#### 2. `app/main.py`

**Intent**: Wire the new router into the existing app instance.

**Contract**: `app.include_router(api.router, prefix="/api")` added alongside the existing `app.frontend("/", directory="dist")` call. Registration order relative to `app.frontend()` doesn't matter (FastAPI always checks path operations first), but the routes stay under `/api` to read unambiguously as API routes.

#### 3. `tests/test_api.py` (new)

**Intent**: Verify the HTTP contract end-to-end against a temporary fixture project directory (a `tmp_path` with a `context/changes/` structure created in the test).

**Contract**: Uses FastAPI's `TestClient`. Covers: `POST` with a valid fixture path returns 200 with correctly parsed changes; `POST` with a path lacking `context/changes` returns 400; `POST` with an already-tracked path returns 400; `GET` after a successful `POST` returns that project in the list.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run pytest tests/test_api.py -v` passes
- [ ] `uv run python -c "import app.main"` succeeds (router wiring doesn't break app construction)

#### Manual Verification:

- [ ] Start `uv run uvicorn app.main:app --reload`, open `http://127.0.0.1:8000/docs`, confirm both `/api/projects` endpoints appear with correct request/response schemas
- [ ] Using the `/docs` "Try it out" UI, `POST` this repo's own path and confirm the real `change.md` data (from `minimal-web-app-scaffold` and this change) comes back correctly, including the `bootstrap-verification` folder being silently skipped

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Frontend UI

### Overview

Extend the existing static `dist/` page with an add-project form and a rendered changes list, wired to the two API endpoints with plain `fetch` — no framework.

### Changes Required:

#### 1. `dist/index.html`

**Intent**: Give the developer a way to submit a path and see results, replacing the static placeholder body while keeping the existing "10xDevTracker" branding.

**Contract**: Adds a form (text input for the path + submit button) and an empty container element for the rendered project/changes list; links `dist/app.js` at the end of `<body>`.

#### 2. `dist/app.js` (new)

**Intent**: Load existing tracked projects on page load and handle new-project submissions, rendering results or inline errors without a page reload.

**Contract**: On `DOMContentLoaded`, `fetch('/api/projects')` and render each project with its changes and raw status strings. On form submit, `fetch('/api/projects', {method: 'POST', ...})` with the input value as `{"path": ...}`; on success, render the returned project and clear the input; on a non-2xx response, show the response's `detail` message inline near the form without clearing the input.

### Success Criteria:

#### Automated Verification:

- [ ] `uv run python -c "import app.main"` succeeds (no backend regression from this phase)
- [ ] Background server boot + `curl` on `/` still returns HTTP 200 with the page content (frontend mount unaffected by the new files)

#### Manual Verification:

- [ ] Open `http://127.0.0.1:8000/`, submit this repo's own path (or another local 10xDEV project), confirm its changes render with correct real `change_id`/`title`/`status` values
- [ ] Submit an invalid path (e.g., one without `context/changes`) and confirm a clear inline error appears with no page reload or crash
- [ ] Reload the page and confirm previously-added projects still appear (persistence round-trip through the real running server, not just the unit tests)

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:

- `app/changes.py`: valid `change.md`, malformed YAML frontmatter, missing required field, folder with no `change.md`.
- `app/projects.py`: path validation (valid / missing `context/changes`), duplicate rejection, JSON persistence round-trip.

### Integration Tests:

- `tests/test_api.py`: full `POST`/`GET` contract against a fixture project directory via FastAPI's `TestClient`.

### Manual Testing Steps:

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/`, submit a real local 10xDEV project path.
3. Confirm the changes list renders with correct real status strings.
4. Submit an invalid path, confirm the inline error message.
5. Reload the page, confirm previously-added projects persist.
6. Open `/docs`, confirm the two new endpoints are documented correctly alongside the existing built-in routes.

## Performance Considerations

None significant at this scale — the PRD's stated target is 1–10 tracked projects with 20–50 changes each, and every read is a handful of small file-system reads and YAML parses per request.

## Migration Notes

None — greenfield feature, no existing tracked-project data or deployed instance to migrate.

## References

- Roadmap: `context/foundation/roadmap.md` (S-01: Add a project path and see per-change status)
- PRD: `context/foundation/prd.md` (FR-001, FR-003, US-01)
- `change.md` schema: `.claude/skills/10x-new/references/change-md.md`
- Prior plan (F-01): `context/changes/minimal-web-app-scaffold/plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Parsing & persistence layer

#### Automated

- [x] 1.1 `uv run pytest tests/test_changes.py -v` passes — 09bcb5c
- [x] 1.2 `uv run pytest tests/test_projects.py -v` passes — 09bcb5c

### Phase 2: API layer

#### Automated

- [x] 2.1 `uv run pytest tests/test_api.py -v` passes — 7d8380c
- [x] 2.2 `uv run python -c "import app.main"` succeeds — 7d8380c

#### Manual

- [ ] 2.3 `/docs` shows both `/api/projects` endpoints with correct schemas
- [ ] 2.4 `POST` via `/docs` against this repo's own path returns correct real change data, `bootstrap-verification` skipped

### Phase 3: Frontend UI

#### Automated

- [x] 3.1 `uv run python -c "import app.main"` succeeds — 83eeb0c
- [x] 3.2 Background server boot + `curl` on `/` returns HTTP 200 — 83eeb0c

#### Manual

- [ ] 3.3 Browser: adding a real project path renders its changes with correct status values
- [ ] 3.4 Browser: invalid path shows inline error, no crash
- [ ] 3.5 Browser: reload persists previously-added projects
