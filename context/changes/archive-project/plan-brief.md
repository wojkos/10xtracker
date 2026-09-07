# Archive/Deactivate Inactive Projects — Plan Brief

> Full plan: `context/changes/archive-project/plan.md`
> Research: `context/changes/archive-project/research.md`

## What & Why

Add a per-project `active` flag so the user can mark a project inactive — skipping its filesystem scans — without removing it, and bring it back later. Directly addresses the original request: projects idle "for sometime" shouldn't be scanned, but removing them outright is too destructive for something the user may pick back up "maybe next week."

## Starting Point

Tracked projects today are a flat JSON array of bare path strings (`data/tracked_projects.json`), with no per-project metadata. Every scan-triggering surface — manual refresh, sync-all, autosync, recommendations, MCP tools — already funnels through one function, `get_project_statuses()`, which makes this a small, well-contained change.

## Desired End State

A project card gets an "Archive" button. Archived projects vanish from the main dashboard and its stats, and are no longer scanned by any code path. They reappear in a new "Archived Projects" section (name/path only) below the Add Project form, with an "Unarchive" button to bring them back into active scanning.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| PRD conflict (parked "archive actions" non-goal) | Proceed now, update PRD/roadmap | The non-goal targets the app acting on a project's own files; this flag is internal dashboard state, not file mutation | Plan |
| Visibility of archived projects | Hidden from main list, shown in a separate section below the Add Project form | Keeps the main view focused while still letting the user find and reactivate archived projects | Plan |
| Archive confirmation | Confirmation dialog, same as Remove | Archiving hides a project from the main view; a confirm step prevents accidental clicks | Plan |
| Unarchive confirmation | No confirmation | Non-destructive — it only resumes scanning, so friction isn't warranted | Plan |
| Migration of existing data | Lazy migrate-on-read | Zero-downtime; matches the codebase's lightweight, script-free persistence style | Plan |
| Summary stats scope | Active projects only | Keeps aggregate counts meaningful and in sync with what's actually scanned | Plan |
| Archived section content | Name/path only, no scan data | Avoids showing misleadingly stale status; nothing is cached today so this avoids new complexity | Plan |

## Scope

**In scope:**
- `active` boolean flag per tracked project, with lazy schema migration
- Filtering the existing scan choke point (`get_project_statuses()`) to active-only
- Archive/Unarchive UI on project cards and a new Archived Projects section
- New API: toggle-active endpoint, lightweight inactive-projects listing
- PRD/roadmap doc reconciliation

**Out of scope:**
- A separate "blocked" state distinct from "archive" (one boolean covers it)
- Caching or displaying last-known scan data for archived projects
- Bulk archive/unarchive actions
- MCP tool changes (they inherit the filtering automatically)
- A standalone migration script

## Architecture / Approach

Follow the existing plain-function persistence pattern (`DATA_FILE` constant + `load_*`/`save_*`, no ORM). A `TrackedProject{path, active}` dataclass replaces the bare `Path`. The single choke point `get_project_statuses()` filters to active projects; a new lightweight function serves the inactive list without triggering any scan. Frontend mirrors the existing Remove button and `removeProject()` fetch-then-reload pattern for both Archive and Unarchive.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Data Model & Persistence | `active` flag with lazy migration, `set_project_active()`, updated tests | Migration must not silently drop or misclassify existing projects |
| 2. Scan Pipeline & API Surface | Active-only filtering at the choke point, toggle + inactive-list endpoints | Missing the one choke point would leave a scan path unfiltered |
| 3. Frontend UI | Archive/Unarchive buttons, new Archived Projects section | Archived cards must not get swept into Sync All/autosync's DOM queries |
| 4. Docs Reconciliation | PRD/roadmap updated to match the shipped feature | Wording must not accidentally re-open the door to full orchestration features |

**Prerequisites:** None — builds directly on the current `master` branch state.
**Estimated effort:** ~1 session across 4 phases (small, well-scoped backend + frontend change).

## Open Risks & Assumptions

- Assumes "archive actions" in the parked roadmap item and this project-level active/inactive toggle are the same conceptual feature (per research's linkage) — Phase 4 narrows the parked item's wording to remove ambiguity going forward.
- Assumes 1-10 tracked projects (per PRD non-functional expectations), so no performance concerns from the added filtering.

## Success Criteria (Summary)

- Archiving a project stops it from being scanned anywhere in the app and removes it from the main view/stats.
- The user can always see and reverse an archive from the Archived Projects section — nothing is destructively removed.
- The feature persists across reloads and works consistently across manual refresh, sync-all, autosync, and MCP read tools.
