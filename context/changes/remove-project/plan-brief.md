# Remove a Project — Plan Brief

> Full plan: `context/changes/remove-project/plan.md`

## What & Why

Let a developer untrack a project they previously added to 10xDevTracker. This is roadmap slice **S-05** (FR-009: "Developer can remove a project from the app") — the app currently has no way to remove a tracked path once added, other than manually editing the JSON data file.

## Starting Point

`app/projects.py` already has `add_tracked_project`, `load_tracked_projects`, and `save_tracked_projects`, and `app/api.py` exposes `POST`/`GET /api/projects`. Projects are identified only by filesystem path (no separate ID). The frontend (`dist/app.js`) renders each tracked project but has no per-project action controls yet.

## Desired End State

Each project on the dashboard has a "Remove" button. Clicking it, after a confirmation prompt, untracks that project and it disappears from the list — persisting across page reloads. Removing never touches the project's own files, only this app's local tracking list.

## Key Decisions Made

| Decision                    | Choice                              | Why (1 sentence)                                                          | Source |
| ---------------------------- | ------------------------------------ | -------------------------------------------------------------------------- | ------ |
| Removal identifier            | JSON body `{"path": str}` on DELETE  | Symmetric with the existing `POST` contract; avoids URL-encoding Windows paths. | Plan   |
| Removing an untracked path    | 404 with `detail` message            | Explicit error contract, consistent with the 400s already used for add errors. | Plan   |
| Confirmation UX                | Native `confirm()` dialog            | One-line guard against accidental clicks, fits the app's minimal vanilla-JS style. | Plan   |

## Scope

**In scope:** `remove_tracked_project` persistence function, `DELETE /api/projects` endpoint, a "Remove" button per project in the UI, case-insensitive path matching consistent with `add_tracked_project`.

**Out of scope:** project ID field or data-format migration, "undo remove", bulk/multi-select removal, styled confirmation modal.

## Architecture / Approach

Same three-layer structure as S-01: pure-Python persistence function → thin FastAPI DELETE route → vanilla-JS button wired with `fetch`. Each phase only depends on the one below it.

## Phases at a Glance

| Phase                  | What it delivers                                      | Key risk                                            |
| ----------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| 1. Persistence layer     | `remove_tracked_project` in `app/projects.py`            | Path-comparison must match `add_tracked_project` exactly or add/remove drift. |
| 2. API layer             | `DELETE /api/projects` returning 200 / 404               | None significant — thin wrapper over Phase 1.        |
| 3. Frontend UI           | "Remove" button per project, confirm-guarded             | Confirm-cancel path must leave state untouched.       |

**Prerequisites:** S-01 (`project-change-status-view`) must be far enough along that projects can be added/listed — currently `implementing`, Phases 1–2 done.
**Estimated effort:** ~1 session across 3 phases; smallest slice on the roadmap (S-05 risk note: "lowest-risk slice").

## Open Risks & Assumptions

- Assumes S-01's persisted `data/tracked_projects.json` format (a plain list of path strings) stays unchanged — if S-01's later phases alter that format, Phase 1 here would need to adjust.

## Success Criteria (Summary)

- A developer can remove a tracked project via the UI and it's gone after reload.
- Removing a path that isn't tracked shows a clear error, not a silent no-op or crash.
- Canceling the confirmation prompt leaves the project untouched.
