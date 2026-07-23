# Configure Autosync Interval — Plan Brief

> Full plan: `context/changes/configure-autosync-interval/plan.md`

## What & Why

Let the developer enable/disable automatic background refresh of the dashboard and set how often it runs (in minutes), instead of having to click "Refresh" on every project manually. This closes out FR-008 / roadmap slice S-08.

## Starting Point

Manual per-project sync already exists (S-06, done): a "Refresh" button re-fetches `GET /api/projects` (which always reads fresh from disk) and patches just that project's DOM. There is no "sync all" endpoint, no scheduler library, and no app-wide settings storage yet — only a bare JSON array of tracked project paths.

## Desired End State

A checkbox + interval input near the top of the dashboard lets the user turn autosync on/off and choose a minute interval. While enabled, every tracked project refreshes automatically on that schedule using the same mechanism as the manual "Refresh" button — one project's failure doesn't block the others or stop the timer. The setting persists and is restored on page reload.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| S-07 dependency gap | Reuse existing full re-fetch (`syncProject()` per tracked path), no new sync-all endpoint | `GET /api/projects` already re-reads everything fresh; building a dedicated endpoint would be scope beyond S-08 | Plan (user-confirmed) |
| Settings persistence | New `data/settings.json` via `app/settings.py`, mirroring `app/projects.py` | Matches existing code conventions; keeps `tracked_projects.json`'s schema untouched | Plan (user-confirmed) |
| Default state | Off by default, 5-minute default interval | Opt-in avoids surprise background network activity on first load | Plan (user-confirmed) |
| Failure handling | Reuse per-project `#sync-error-{path}` UI, timer keeps running | Consistent UX with manual sync, no new error-handling code path | Plan (user-confirmed) |
| UI placement | Small control near the top of the dashboard, not a separate settings panel | Discoverable near existing sync actions, minimal new layout | Plan (user-confirmed) |
| Interval bounds | 1–1440 minutes, validated server-side | Prevents a zero/negative or absurdly large interval from being persisted | Plan |

## Scope

**In scope:**
- Enable/disable autosync + interval (minutes) control in the UI
- Server-side persistence of the setting (`GET`/`PUT /api/settings`)
- Frontend timer that reuses the existing per-project sync function across all tracked projects

**Out of scope:**
- A dedicated backend "sync all" endpoint
- Backend scheduler / background tasks (autosync only runs while the tab is open)
- Retry/backoff logic on sync failure
- Per-project autosync intervals
- Multi-tab coordination

## Architecture / Approach

Backend: `app/settings.py` (new, mirrors `app/projects.py`) + two routes in `app/api.py` (`GET`/`PUT /api/settings`) for reading/writing `{enabled, interval_minutes}` to `data/settings.json`, with server-side bounds validation (1–1440 minutes). Frontend: a checkbox + number input in `dist/index.html`, wired in `dist/app.js` to load/save settings and drive a `setInterval` loop whose tick calls the existing `syncProject(path)` once per currently-rendered project — no new sync logic, just orchestration.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Backend settings persistence + API | `GET`/`PUT /api/settings` with validated, persisted enabled/interval state | Low — small, isolated module following an established pattern exactly |
| 2. Frontend autosync controls + timer | UI toggle + interval input driving a client-side autosync loop | Timer/state bugs (e.g. not clearing the old interval before rescheduling) are the main risk; mitigated by manual verification steps covering reschedule and reload |

**Prerequisites:** Phase 1 must land before Phase 2 (frontend depends on the settings API existing).
**Estimated effort:** ~1 session across 2 phases — small, additive change on an existing, well-understood codebase.

## Open Risks & Assumptions

- Autosync only runs while the dashboard tab is open and in memory — if the user wants "always-on" refresh regardless of the browser, that would require a backend scheduler, which is explicitly out of scope here.
- Interval bounds (1–1440 minutes) were chosen as sensible defaults, not requested explicitly by the user — revisit if a different range is needed later.

## Success Criteria (Summary)

- User can enable autosync, set an interval, and see the dashboard refresh automatically on that schedule without clicking "Refresh".
- A single broken project's sync failure during autosync doesn't stop other projects from updating or stop the timer.
- The setting survives a page reload.
