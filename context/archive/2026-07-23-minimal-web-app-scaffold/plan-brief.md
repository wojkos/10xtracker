# Minimal Web App Scaffold — Plan Brief

> Full plan: `context/changes/minimal-web-app-scaffold/plan.md`

## What & Why

Replace the current `uv init` hello-world stub with a real, running FastAPI app that serves a single browser-viewable placeholder page. This is roadmap item **F-01** — the foundation slice everything else (S-01 through S-08, the actual project-status dashboard) depends on, since nothing can be user-visible until something runs and renders in a browser.

## Starting Point

`main.py` today is a plain `print("Hello from 10xtracker!")` script with no FastAPI app instance, even though `fastapi` and `uvicorn` are already declared dependencies in `pyproject.toml`. No `app/` package, no static/template directory, and no test tooling exist yet. `README.md` is empty.

## Desired End State

`uv run uvicorn app.main:app --reload` boots the app, and opening `http://127.0.0.1:8000/` in a browser shows a minimal "10xDevTracker" branded placeholder page. `README.md` documents that command.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| Page-serving mechanism | FastAPI's `app.frontend()` serving a `dist/` directory | Matches `tech-stack.md`'s stated plan to have FastAPI serve static files for a future JS/TS frontend — confirmed as FastAPI's own documented pattern for exactly this scenario. |
| Project structure | `app/__init__.py` + `app/main.py` package, `dist/` at repo root | This is FastAPI's own recommended layout for the "serve a static frontend later" scenario — adopting it now avoids a restructuring commit when S-01 lands. |
| Automated tests | None for this scaffold | User explicitly opted out; deferred until S-01 introduces real logic worth testing. |
| Placeholder content | Minimal branded page ("10xDevTracker") rather than bare text | Gives manual verification something concrete to check for beyond "a page loaded". |

## Scope

**In scope:**
- `app/main.py` FastAPI instance with `app.frontend()` mount
- `dist/index.html` branded placeholder page
- Removing the stale root `main.py`
- `README.md` run instructions

**Out of scope:**
- Any actual JS/TS frontend framework or build tooling
- API endpoints or business logic (reading `changes/`, `roadmap.md`, etc. — that's S-01)
- Automated tests, `.gitignore`, CI/CD, deployment config

## Architecture / Approach

A single FastAPI instance in `app/main.py` mounts a sibling `dist/` directory via `app.frontend("/", directory="dist")`. FastAPI checks registered path operations before falling back to frontend files, so this coexists cleanly with `/docs` now and with any `/api`-prefixed routes S-01 adds later — no code here needs to change when the real frontend build replaces the hand-written `dist/index.html`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. App scaffold & page serving | `app/` package, `dist/index.html`, FastAPI instance, stale `main.py` removed | Mixing up path-operation vs. frontend-mount precedence — mitigated since FastAPI always checks path operations first |
| 2. Run & manual verification | Confirmed boot, documented run command in `README.md` | None significant — thin verification/documentation phase |

**Prerequisites:** None — this is the first change in the roadmap (F-01), no dependencies.
**Estimated effort:** ~1 short session, single phase pair.

## Open Risks & Assumptions

- Assumes the installed `fastapi>=0.139.2` includes `app.frontend()` — confirmed present in the live FastAPI docs at plan-writing time, but worth a quick sanity check if the pinned version ever changes.

## Success Criteria (Summary)

- `uv run uvicorn app.main:app --reload` boots without errors
- Browser shows the branded placeholder at `http://127.0.0.1:8000/`, and `/docs` still works
- `README.md` accurately documents how to run it
