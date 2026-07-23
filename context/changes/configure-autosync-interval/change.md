---
change_id: configure-autosync-interval
title: Configure autosync interval
status: planned
created: 2026-07-23
updated: 2026-07-23
archived_at: null
---

## Notes

Roadmap item S-08 — configure how often (in minutes) the app automatically refreshes project status. Depends on S-07 (`sync-all-projects`, proposed — not yet built) per `context/foundation/roadmap.md`, but `GET /api/projects` already re-reads every tracked project fresh from disk, so this change reuses that existing endpoint (looping the existing per-project `syncProject()` sync across all tracked projects on a client-side timer) instead of waiting on a dedicated sync-all backend route.
