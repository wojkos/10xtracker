---
date: 2026-09-07T00:00:00+02:00
researcher: Wojciech Kostanski
git_commit: 9eff58be8b0945e760d3e15c43385497084b0764
branch: master
repository: 10xtracker
topic: "Possibilities to add an inactive/archived-project flag that skips folder scanning"
tags: [research, codebase, projects, scanning, api, frontend]
status: complete
last_updated: 2026-09-07
last_updated_by: Wojciech Kostanski
---

# Research: Possibilities to add an inactive/archived-project flag that skips folder scanning

**Date**: 2026-09-07
**Researcher**: Wojciech Kostanski
**Git Commit**: 9eff58be8b0945e760d3e15c43385497084b0764
**Branch**: master
**Repository**: 10xtracker

## Research Question

The change note in [change.md](change.md) says: *"Some project are not in work for sometime and there is no point to scan their folders. I would like to have possibility to block/archive as the other option then remove — maybe next week I will back to work etc."*

This research checks the possibilities for adding a single "inactive" flag per tracked project (per user's scoping choice: one combined state, not separate block/archive states) that lets the scanner skip that project's filesystem reads, across the full stack (data model, scan pipeline, API, frontend).

## Summary

The tracked-project list is currently the simplest possible shape — a flat JSON array of path strings (`data/tracked_projects.json`) — with **no per-project metadata slot at all**. Adding an `active`/`inactive` boolean therefore requires a small data-shape migration (array of strings → array of `{path, active}` objects), not just a new field. Every scan-triggering surface in the app (manual refresh, sync-all, the client-side autosync timer, recommendations, and the MCP `get_project_status` tool) funnels through exactly one function — `get_project_statuses()` in [app/project_status.py:27-29](app/project_status.py#L27-L29) — which is the single correct choke point to skip inactive projects. No server-side scheduler exists; autosync is a client-side `setInterval` that just re-hits `GET /api/projects`, so a backend-only fix at the choke point is sufficient to cover autosync too. On the frontend, `dist/` is hand-written (no build step), and the natural place for an "Archive"/"Unarchive" toggle button is next to the existing Refresh/Remove buttons in `renderProjectSection()` ([dist/app.js:133-160](dist/app.js#L133-L160)).

One important caveat surfaced by historical context: the PRD explicitly parks "archive actions" as a v2+/non-goal item (see Historical Context below) — this is worth flagging back to the user before planning, not a blocker to the research itself.

## Detailed Findings

### Project data model & persistence

- A tracked project is **just a `pathlib.Path`** — no dataclass, no Pydantic model, no metadata fields ([app/projects.py:4](app/projects.py#L4)).
- Storage: `data/tracked_projects.json`, a flat JSON array of path strings.
  - `load_tracked_projects()` ([app/projects.py:13-17](app/projects.py#L13-L17)) → `[]` if missing, else `[Path(p) for p in raw]`.
  - `save_tracked_projects(paths)` ([app/projects.py:20-24](app/projects.py#L20-L24)) → `json.dumps([str(p) for p in paths], indent=2)`.
- `add_tracked_project(path)` ([app/projects.py:27-36](app/projects.py#L27-L36)): validates `<path>/context/changes` exists, resolves path, case-insensitive dedup check, appends, saves.
- `remove_tracked_project(path)` ([app/projects.py:39-49](app/projects.py#L39-L49)): resolves, filters by case-insensitive path match, raises if not found, saves.
- `app/settings.py` is a **separate** JSON file (`data/settings.json`) storing `{enabled: bool, interval_minutes: int}` for autosync — same "module-level `DATA_FILE` constant + plain `load_*`/`save_*` functions" pattern, not shared code with `projects.py` ([app/settings.py:4-28](app/settings.py#L4-L28)).
- Only consumers of `app.projects` are `app/api.py` and `app/project_status.py` — no other module reads/writes the tracked-project list directly.
- `ProjectResponse` (the API-facing model, not the persisted one) lives in [app/project_status.py:9-12](app/project_status.py#L9-L12): `{path: str, name: str, changes: list[ChangeSummary]}` — this is where an `active`/`archived` field would also need to surface for the UI to render it.

**Implication**: `data/tracked_projects.json` must migrate from `list[str]` to something like `list[{"path": str, "active": bool}]`, touching `load_tracked_projects`/`save_tracked_projects`/`add_tracked_project`/`remove_tracked_project` and the two call sites in `app/api.py` and `app/project_status.py`. `tests/test_projects.py` round-trip assertions on bare `Path` lists will also need updating.

### Scan pipeline and the single choke point

Call graph: `get_project_statuses()` → `get_project_status(path)` (per project) → `list_changes(context_dir)` → `get_roadmap_correlations` (once per project) + `get_phase_progress` (once per change). `app/recent_work.py` and `app/workflow_recommendations.py` both re-invoke `get_project_statuses()` internally (redundant re-scans, but structurally irrelevant to this feature since they still route through the same function).

- Root fan-out: [app/project_status.py:27-29](app/project_status.py#L27-L29):
  ```python
  def get_project_statuses() -> list[ProjectResponse]:
      statuses = [get_project_status(path) for path in load_tracked_projects()]
      return sorted(statuses, key=_latest_update, reverse=True)
  ```
- No caching/memoization exists anywhere in `app/` — the closest reusable idiom is the guard-clause style already used in `list_changes` ([app/changes.py:67-68](app/changes.py#L67-L68)): `if not changes_dir.is_dir(): return []`.
- **No server-side sync/scheduler function exists.** All three "sync" UI flows (manual refresh, sync-all, autosync) are client-side wrappers that just call `GET /api/projects` — see API section below. This means autosync doesn't need separate handling; filtering in `get_project_statuses()` covers it automatically.

**Recommended choke point**: filter in `get_project_statuses()` itself (not in `load_tracked_projects()`, which is also used by add/remove logic that must still see inactive projects; and not in `get_project_status()`, which the add-project flow calls directly on a freshly added path and must always scan regardless of stored state):

```python
def get_project_statuses() -> list[ProjectResponse]:
    statuses = [
        get_project_status(entry.path)
        for entry in load_tracked_projects()
        if not entry.inactive
    ]
    return sorted(statuses, key=_latest_update, reverse=True)
```

This single guard covers manual sync, sync-all, autosync, `/api/recommendations`, `get_recent_work`, and the MCP `get_project_status`/`get_next_10x_action` tools, since all of them converge on this one function.

### API surface

FastAPI app ([app/main.py](app/main.py), 9 lines total): routes mounted via `app.include_router(api.router, prefix="/api")` ([app/main.py:7](app/main.py#L7)); static SPA served from `dist/` ([app/main.py:9](app/main.py#L9)); MCP transport bolted on separately ([app/main.py:8](app/main.py#L8)). **No background scheduler/thread anywhere** — confirmed via grep, no `Thread`/`BackgroundTasks`/`asyncio.create_task`.

Existing route table (all under `/api`, defined in [app/api.py](app/api.py)):

| Method | Path | Handler | Line |
|---|---|---|---|
| POST | `/projects` | `add_project` | [api.py:28-34](app/api.py#L28-L34) |
| GET | `/projects` | `list_projects` | [api.py:37-39](app/api.py#L37-L39) |
| DELETE | `/projects` | `remove_project` | [api.py:42-48](app/api.py#L42-L48) |
| GET | `/recommendations` | `get_recommendations` | [api.py:51-53](app/api.py#L51-L53) |
| GET | `/settings` | `get_settings` | [api.py:56-59](app/api.py#L56-L59) |
| PUT | `/settings` | `update_settings` | [api.py:62-68](app/api.py#L62-L68) |

There is no dedicated per-project sync endpoint — `GET /api/projects` always re-parses everything live, so "sync" is really just "re-fetch." A new toggle-active endpoint (e.g. `PUT /api/projects/active` taking `{path, active}`, following the existing `ProjectPathRequest`-style body pattern at [api.py:14-16](app/api.py#L14-L16)) would sit naturally alongside the existing POST/DELETE `/projects` handlers.

`app/mcp.py` exposes `get_project_status` (→ `get_project_statuses()`), `get_recent_work`, and `get_next_10x_action` as read-only MCP tools ([app/mcp.py:53-92](app/mcp.py#L53-L92)) — all reuse the same `ProjectResponse`/pipeline, so they'd pick up the new field automatically with no MCP-specific change needed. No MCP write/mutate tool exists today (a historical change, `2026-07-27-app-as-mcp`, explicitly excluded "archive" from MCP's scope), so this feature doesn't need to touch `mcp.py`.

### Frontend project list UI

`dist/` is **hand-written source**, not a build artifact — no `package.json`, no bundler config, no `src/`. Plain vanilla JS with `document.createElement` DOM construction (no template literals, no framework).

- `renderProjectSection(project)` ([dist/app.js:114-196](dist/app.js#L114-L196)) is the single-project-card renderer. The `.project-controls` div ([dist/app.js:133-160](dist/app.js#L133-L160)) currently holds a **Refresh** button ([136-145](dist/app.js#L136-L145)) and a **Remove** button ([153-160](dist/app.js#L153-L160)) — a new Archive/Unarchive button belongs here, right after `controls.appendChild(removeBtn)`.
- The card header has a click handler that toggles the expand/collapse details panel, explicitly guarded so clicks inside `.project-controls` don't trigger it ([app.js:183-185](dist/app.js#L183-L185)) — any new button must live inside `.project-controls` to inherit this guard for free.
- `syncProject`/`syncAllProjects`/autosync ([app.js:209-269](dist/app.js#L209-L269), [271-328](dist/app.js#L271-L328), [477-506](dist/app.js#L477-L506)) all just call `fetch("/api/projects")` and re-render — no per-project sync endpoint to update.
- `removeProject` ([app.js:330-360](dist/app.js#L330-L360)) is the closest existing pattern for a new "toggle active" handler: `window.confirm` (optional for archive, arguably not needed since it's reversible) → `fetch("/api/projects", {...})` → reload via `loadProjects()`.
- No colored status-badge pattern exists (`renderSummaryStats`, [app.js:55-77](dist/app.js#L55-L77), only builds plain text); the only pill-shaped element is `.count-badge` ([dist/style.css:179-188](dist/style.css#L179-L188)), reusable with a muted palette for an "Inactive" indicator. `.remove-btn` styling ([style.css:61-73](dist/style.css#L61-L73)) is the closest button-style precedent for a secondary action.
- `dist/index.html:39` has `<div id="projects"></div>` as the empty container populated entirely by `renderProjects()` — no markup changes needed there.

## Code References

- [app/projects.py:4-49](app/projects.py#L4-L49) — tracked-project storage, CRUD (bare `Path` list, JSON file)
- [app/project_status.py:9-29](app/project_status.py#L9-L29) — `ProjectResponse` model and `get_project_statuses()` choke point
- [app/settings.py:4-28](app/settings.py#L4-L28) — sibling persistence pattern to mirror (boolean `enabled` + JSON file)
- [app/changes.py:65-83](app/changes.py#L65-L83) — per-project change scanning, guard-clause idiom to reuse
- [app/api.py:14-68](app/api.py#L14-L68) — full existing route table and request models
- [app/main.py:1-9](app/main.py#L1-L9) — FastAPI wiring, confirms no server-side scheduler
- [app/mcp.py:53-92](app/mcp.py#L53-L92) — MCP tools that reuse the same pipeline (read-only)
- [dist/app.js:114-196](dist/app.js#L114-L196) — `renderProjectSection`, insertion point for a new toggle button
- [dist/app.js:330-360](dist/app.js#L330-L360) — `removeProject`, closest handler pattern to copy
- [dist/style.css:61-73](dist/style.css#L61-L73), [179-188](dist/style.css#L179-L188) — existing button/badge styles to reuse
- [tests/test_projects.py](tests/test_projects.py) — round-trip tests asserting `list[Path]` shape; will need updating for the new schema

## Architecture Insights

- The codebase has a strict, repeated convention for simple persistence: a module-level `DATA_FILE` constant plus plain `load_*`/`save_*` functions, no classes, `mkdir(parents=True, exist_ok=True)` before write (used identically in `app/projects.py` and `app/settings.py`). Any new persisted flag should follow this exact shape rather than introducing an ORM/class-based model.
- The app has exactly one aggregation choke point (`get_project_statuses()`) that all read paths (REST, MCP, recommendations, recent-work) converge on — a rare case where a single, small guard clause has full-system reach.
- There is no true "sync" concept server-side today — every "sync" action from the UI is actually just a fresh `GET /api/projects`, since nothing is cached. This simplifies the feature: skipping a project in `get_project_statuses()` is sufficient; there's no separate cache to invalidate.
- Per-change status already has a 9-value enum including a value literally named `archived` (documented in `.claude/skills/10x-new/references/change-md.md` and `context/archive/2026-07-23-project-change-status-view/plan.md`). That enum is scoped to *changes inside* a project, not the project itself — reusing the name `archived` or `status` for the new project-level flag risks conceptual collision (a project could have `archived` changes while remaining an active project). A boolean `active`/`inactive` name (mirroring `settings.py`'s `enabled` boolean) is more consistent and avoids ambiguity.

## Historical Context (from prior changes)

- [context/foundation/roadmap.md:197](context/foundation/roadmap.md#L197) explicitly **parks** "Archive actions from the UI": *"Why parked: PRD Non-Goals — 'Not an orchestration tool'; the app visualizes only, archiving stays outside the app. Also listed as v2+ in Success Criteria."*
- [context/foundation/prd.md:42](context/foundation/prd.md#L42) (Secondary Success Criteria): *"None for v1. Autosync reliability, archive actions, and export are v2+ features."* And Non-Goals ([prd.md:111](context/foundation/prd.md#L111)): *"Not an orchestration tool: The app does not trigger actions (archiving, creating changes, updating status). It visualizes only."*
- `context/archive/2026-07-23-remove-project/plan.md:12` and its `plan-brief.md:11`: *"Projects are identified only by their filesystem path — there is no separate ID field anywhere in the model, so removal must key off the same path string."* Confirms the path-only model is a long-standing, deliberate constraint, not an oversight.
- `context/archive/2026-07-23-configure-autosync-interval/plan.md:20`: names the `app/projects.py` pattern (module-level `DATA_FILE`, plain `load_*`/`save_*`, no classes) as *"the established convention to mirror for new settings storage"* — this is the same convention this feature should follow for the migrated schema.
- `context/archive/2026-07-27-app-as-mcp/plan.md:32`: MCP tools explicitly exclude "add, remove, edit, sync, archive, or otherwise mutate projects" — confirms this feature doesn't need MCP write support, only automatic read pass-through.
- No `context/foundation/lessons.md` exists in this repo.
- `context/changes/archive-project/` (this change) is brand new today, `change.md` only, no prior plan/research — this research document is the first artifact for it.

## Related Research

None yet — this is the first research artifact for `archive-project`.

## Open Questions

1. **PRD conflict**: the PRD/roadmap explicitly deferred "archive actions" as v2+ and listed it as a non-goal ("not an orchestration tool"). Should the plan proceed as a deliberate scope override (and note it in the PRD/roadmap), or should the PRD be amended first? Worth a decision before `/10x-plan`.
2. **Naming**: confirm `active`/`inactive` (boolean) as the field name, to avoid colliding with the per-change `status` enum's `archived` value (see Architecture Insights).
3. **Data migration**: is a one-time migration script needed for existing `data/tracked_projects.json` files (array of strings → array of objects), or is a "migrate on first read" fallback in `load_tracked_projects()` acceptable? Not investigated here — recommend deciding during planning.
4. **UI reversibility**: should toggling inactive require a confirmation dialog (like Remove does), or should it be a lightweight, instantly-reversible toggle given the user's stated use case ("maybe next week I will back to work")? Leans toward no confirmation, but worth confirming during planning.
