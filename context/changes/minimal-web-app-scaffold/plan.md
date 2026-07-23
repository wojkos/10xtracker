# Minimal Web App Scaffold Implementation Plan

## Overview

Replace the current `uv init` hello-world stub with a real, running FastAPI application that serves a single browser-viewable placeholder page. This is roadmap item **F-01** — the foundation every later slice (S-01 through S-08) depends on, since nothing else can be user-visible until something actually runs and renders in a browser.

## Current State Analysis

- [main.py](main.py) is a plain script (`print("Hello from 10xtracker!")`) with no FastAPI `app` instance and no routes, despite `fastapi>=0.139.2` and `uvicorn>=0.51.0` already being declared dependencies in [pyproject.toml](pyproject.toml).
- No `app/` package, no `dist/` or `static/` directory, no templates exist anywhere in the repo.
- [README.md](README.md) is empty (0 bytes) — no run instructions exist yet.
- No test tooling (pytest, httpx) is configured in `pyproject.toml`.
- No `.gitignore` exists.

## Desired End State

A `uv run uvicorn app.main:app --reload` command boots a FastAPI app that serves a minimal, branded "10xDevTracker" placeholder page at `http://127.0.0.1:8000/`, with FastAPI's built-in `/docs` and `/openapi.json` routes still functioning normally alongside it. `README.md` documents the run command. The stale root `main.py` stub is gone.

**Verification**: run the documented command, open the page in a browser, see the branded placeholder (not a 404 or FastAPI's default JSON response).

### Key Discoveries:

- [main.py:1-6](main.py) today is a plain script with no FastAPI app instance at all — the FastAPI/uvicorn dependencies in `pyproject.toml` are currently unused.
- [tech-stack.md](../../foundation/tech-stack.md)'s stated intention — "you'll add a separate JS/TS frontend later and have FastAPI serve the static files" — maps directly onto FastAPI's own `app.frontend()` helper (confirmed against the live docs at https://fastapi.tiangolo.com/tutorial/frontend/), which serves a pre-built static directory and auto-detects an `index.html`/`404.html` fallback — no manual `StaticFiles` mount needed.
- FastAPI's own docs recommend exactly this layout for the scenario described in `tech-stack.md`: `app/__init__.py` + `app/main.py` next to a sibling `dist/` directory holding the servable frontend output. Adopting it now avoids a restructuring commit when S-01 introduces the first real endpoints.
- [roadmap.md](../../foundation/roadmap.md)'s Risk note for F-01 explicitly caps scope at "one app instance + one servable page" — reinforcing the smallest possible `app/` + `dist/` shape rather than templating, routers, or config layers.

## What We're NOT Doing

- No Jinja2 or any template engine — decided against in favor of `app.frontend()` static serving.
- No actual JS/TS frontend framework or build tooling — out of scope for F-01; `dist/index.html` is hand-written as a stand-in for the future build output.
- No automated tests (pytest/httpx) — explicitly deferred; this scaffold relies on manual verification only.
- No API endpoints, data reading, or business logic for parsing `changes/`/`roadmap.md` — that's S-01's job.
- No `.gitignore`, CI/CD, or deployment config — deferred per `tech-stack.md` and roadmap Baseline.
- No `[project.scripts]` entry point or other packaging changes beyond the `app/` module move.

## Implementation Approach

Move the FastAPI app into an `app/` package following FastAPI's own documented layout for this exact "serve a static frontend later" scenario, mount a `dist/` directory via `app.frontend()`, hand-write a minimal branded `dist/index.html` as the current placeholder, retire the stale root `main.py`, and verify the app boots and renders correctly before documenting the run command in `README.md`.

## Critical Implementation Details

**Frontend mount vs. future API routes**: `app.frontend()` mounted at `"/"` only serves frontend files when no path operation matches — FastAPI always checks registered path operations first, regardless of registration order. This means mounting the frontend at `"/"` now is safe and won't need to move later, but when S-01 adds real API endpoints, they should get an explicit prefix (e.g. `/api/...`) so they read unambiguously as API routes rather than risking a same-path collision with future frontend routes.

## Phase 1: App scaffold & page serving

### Overview

Create the `app/` package with a real FastAPI instance, mount a `dist/` directory as the servable frontend, add the placeholder page, and retire the stale root stub.

### Changes Required:

#### 1. `app/__init__.py`

**Intent**: Mark `app/` as a Python package.

**Contract**: Empty file.

#### 2. `app/main.py`

**Intent**: Instantiate the FastAPI application and serve the `dist/` directory as the app's frontend, so the eventual JS/TS frontend build can be dropped into `dist/` later with no code changes here.

**Contract**: Module exposes a module-level `app = FastAPI()` instance, then calls `app.frontend("/", directory="dist")`. This is the ASGI entrypoint referenced as `app.main:app`. No explicit `fallback=` argument needed — FastAPI's default `fallback="auto"` detects the single `index.html` correctly for this single-page placeholder.

#### 3. `dist/index.html`

**Intent**: Minimal branded placeholder confirming the scaffold runs, giving manual verification something specific to check for.

**Contract**: Static HTML page with a title/heading referencing "10xDevTracker" and body text indicating the foundation scaffold is running.

#### 4. `main.py` (repo root)

**Intent**: Remove the stale `uv init` hello-world stub — nothing references it as an entry point (`pyproject.toml` defines no `[project.scripts]`), and `app/main.py` is now the real entrypoint.

**Contract**: File deleted.

### Success Criteria:

#### Automated Verification:

- `uv run python -c "import app.main"` succeeds with no exceptions (confirms the module imports cleanly and the FastAPI app builds)
- `dist/index.html` exists on disk

#### Manual Verification:

- Running `uv run uvicorn app.main:app --reload` and opening `http://127.0.0.1:8000/` in a browser shows the branded "10xDevTracker" placeholder (not a 404 or FastAPI's default JSON response)
- `http://127.0.0.1:8000/docs` still loads FastAPI's auto-generated docs UI, confirming built-in routes coexist correctly with the frontend mount at `"/"`

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Run & manual verification

### Overview

Confirm the scaffold boots cleanly end-to-end via the documented command and record that command in `README.md`, which is currently empty.

### Changes Required:

#### 1. `README.md`

**Intent**: Give the next developer (or future self) the one command needed to run the app, since the file is currently empty.

**Contract**: Documents the dev-server command `uv run uvicorn app.main:app --reload` and the URL it serves (`http://127.0.0.1:8000/`).

### Success Criteria:

#### Automated Verification:

- Start `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` in the background, `curl` the root path and confirm an HTTP 200 response containing the "10xDevTracker" placeholder text, then stop the server

#### Manual Verification:

- Open `http://127.0.0.1:8000/` in a browser and visually confirm the placeholder page renders with no console errors
- Follow the instructions in `README.md` fresh (stop any running server first) and confirm they're accurate as written

---

## Testing Strategy

### Unit Tests:

- None for this scaffold — explicitly deferred per user decision. S-01 onward introduces real logic worth unit-testing.

### Integration Tests:

- None — the Phase 2 automated `curl` boot-check is the only scripted verification; deeper integration tests apply once there's an API to test.

### Manual Testing Steps:

1. Run `uv run uvicorn app.main:app --reload`.
2. Open `http://127.0.0.1:8000/` — confirm the branded placeholder renders.
3. Open `http://127.0.0.1:8000/docs` — confirm FastAPI's built-in docs UI still loads.
4. Stop the server, follow `README.md`'s instructions fresh to restart it.

## Performance Considerations

None — a single static placeholder page has no meaningful performance surface at this scale.

## Migration Notes

None — no existing data, users, or deployed instance. This replaces an unused stub script with a running app.

## References

- Roadmap: `context/foundation/roadmap.md` (F-01: Minimal web app scaffold)
- Tech stack: `context/foundation/tech-stack.md`
- FastAPI frontend serving docs: https://fastapi.tiangolo.com/tutorial/frontend/
- Bootstrap verification: `context/changes/bootstrap-verification/verification.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: App scaffold & page serving

#### Automated

- [x] 1.1 `uv run python -c "import app.main"` succeeds — 06de947
- [x] 1.2 `dist/index.html` exists on disk — 06de947

#### Manual

- [x] 1.3 Browser shows branded "10xDevTracker" placeholder at `http://127.0.0.1:8000/` — 06de947
- [x] 1.4 `http://127.0.0.1:8000/docs` still loads alongside the frontend mount — 06de947

### Phase 2: Run & manual verification

#### Automated

- [x] 2.1 Background server boot + `curl` root returns HTTP 200 with placeholder text — cfe288f

#### Manual

- [ ] 2.2 Browser placeholder renders with no console errors
- [ ] 2.3 `README.md` instructions followed fresh and confirmed accurate
