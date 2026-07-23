# Add a Project Path and See Per-Change Status — Plan Brief

> Full plan: `context/changes/project-change-status-view/plan.md`

## What & Why

Add the first real feature to 10xDevTracker: a developer submits a local 10xDEV project path, the app validates it, reads its `context/changes/*/change.md` files, and shows each change with its raw status. This is roadmap item **S-01**, the north-star slice — it proves the app can correctly parse a real `context/changes/` directory before anything else (aggregation, phase progress, roadmap correlation, sync) gets built on top of it.

## Starting Point

The app today (F-01, implemented) is a bare FastAPI instance serving a static branded placeholder page from `dist/` — no API routes, no data-parsing logic, no persistence, and no YAML or test tooling in `pyproject.toml`. This change is the first to touch actual business logic.

## Desired End State

A developer opens `http://127.0.0.1:8000/`, submits a project root path via a form, and sees that project's changes render with their real `change.md` status strings. An invalid path shows a clear inline error. Reloading the page still shows previously-added projects.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Status display | Raw pass-through of all 9 `change.md` status values, no bucketing | User chose accuracy to source over the PRD's illustrative 3-bucket framing; bucketed counts are S-02's job, not S-01's | Plan |
| Persistence | Local JSON file (`data/tracked_projects.json`) | User wants tracked projects to survive a server restart | Plan |
| Invalid path handling | Reject at add-time with an inline error | Fails fast, keeps the tracked list always valid, matches the app's read-only guardrail | Plan |
| Frontend approach | Vanilla JS + `fetch` against a JSON API, no framework | No build tooling needed now; the same JSON API serves the real JS/TS frontend `tech-stack.md` plans to add later | Plan |
| FR-001 vs. US-01 path ambiguity | Project root (containing `context/`) is the input, not the `context/` dir itself | FR-001's explicit wording is treated as authoritative over the US-01 example path | Plan |
| Malformed/missing `change.md` | Missing → folder skipped; malformed → included with an `error` flag | This repo's own `bootstrap-verification` folder has no `change.md`, proving the parser must tolerate this on real data | Plan |
| Testing | `pytest` + `httpx` introduced now | F-01's plan explicitly deferred testing "until S-01 introduces real logic worth testing" | Plan |

## Scope

**In scope:**
- Path validation (must contain `context/changes/`)
- `change.md` frontmatter parsing, tolerant of missing/malformed files
- JSON-file persistence of tracked project paths
- `POST /api/projects` and `GET /api/projects` JSON endpoints
- Vanilla-JS add-project form and rendered changes list on the existing static page
- First `.gitignore`, first test suite (`pytest` + `httpx`)

**Out of scope:**
- Status bucketing/aggregation (S-02), phase/task progress from `plan.md` (S-03), roadmap correlation (S-04), project removal (S-05), manual/auto sync (S-06/07/08)
- Any JS/TS frontend framework or build tooling
- Scanning `context/archive/`

## Architecture / Approach

Three layers, each depending only on the one below: a pure-Python parsing/persistence layer (`app/changes.py`, `app/projects.py`, unit-tested), a thin FastAPI JSON layer (`app/api.py`, `/api`-prefixed, integration-tested with `TestClient`), and a vanilla-JS addition to `dist/` that calls those two endpoints. `GET /api/projects` always re-reads from disk live — there's no caching layer to invalidate, so "sync" stays a clean, separate concept for later slices.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Parsing & persistence layer | `change.md` parsing + JSON-backed tracked-project list, unit-tested | A malformed real-world `change.md` breaking the whole read — mitigated by per-folder error isolation |
| 2. API layer | `POST`/`GET /api/projects`, integration-tested | None significant — thin HTTP wrapper over an already-tested logic layer |
| 3. Frontend UI | Add-project form + rendered list on the existing static page | Hand-rolled DOM updates without a framework — acceptable given the small surface (one form, one list) |

**Prerequisites:** F-01 (`minimal-web-app-scaffold`), already implemented.
**Estimated effort:** ~2-3 sessions across 3 phases.

## Open Risks & Assumptions

- Assumes `data/tracked_projects.json` is an acceptable persistence mechanism for a single-user local tool; if multiple browser tabs/processes write concurrently, there's no locking — acceptable at this scale but worth revisiting if usage patterns change.
- The FR-001/US-01 path-input ambiguity was resolved in favor of FR-001 (project root, not the `context/` dir); if the user actually intended the `context/` dir itself, path validation logic in Phase 1 would need a one-line adjustment.

## Success Criteria (Summary)

- Developer can add a real local 10xDEV project path via the UI and see its changes with correct real status values
- Invalid paths produce a clear inline error, not a crash
- Previously-added projects persist across a page reload
