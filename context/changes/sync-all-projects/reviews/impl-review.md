<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Sync All Projects

- **Plan**: context/changes/sync-all-projects/plan.md
- **Scope**: Phase 1-3 of 3 (full plan)
- **Date**: 2026-07-24
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS (manual checks still pending in Progress) |

## Findings

### F1 — `syncAllProjects()` has no try/finally reset for `syncingAll`

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:252-298
- **Detail**: Every other async DOM-driving function in this file (`syncProject`, `removeProject`, `saveAutosyncSettings`) wraps its body in try/catch/finally so state resets even on unexpected failure. `syncAllProjects()` sets `syncingAll = true` (line 264) and only resets it at the tail of the function (line 293) with no `finally`. If anything between those lines throws (e.g. a future refactor removes `sync-all-btn` from the DOM, or `Promise.allSettled` itself throws), `syncingAll` stays `true` forever and the "Sync All" button plus every per-project refresh button stay disabled with no recovery short of a page reload.
- **Fix**: Wrap the body from `syncingAll = true` through the final re-enable block in try/finally, resetting `syncingAll = false` and re-enabling the buttons in the `finally` block.
- **Decision**: FIXED

### F2 — `#dashboard-controls` not right-aligned per plan contract

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: dist/style.css:201-211
- **Detail**: Phase 3's contract explicitly said to style `#dashboard-controls` "right-aligned." The implemented CSS is `display: flex; align-items: center; gap: 1rem;` with no `justify-content: flex-end` or `margin-left: auto` — it renders left-aligned, matching the existing `#autosync-controls` block instead.
- **Fix**: Either add `justify-content: flex-end` to `#dashboard-controls` to match the plan's contract, or accept the left-aligned layout as intentional (it's visually consistent with the adjacent `#autosync-controls` section) and treat the plan wording as superseded.
- **Decision**: FIXED (Fix A)

### F3 — No mutual exclusion between `syncAllProjects` and `autosyncAll`

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:252 (syncAllProjects) vs dist/app.js:362 (autosyncAll)
- **Detail**: If the autosync timer fires while a manual "Sync All" is in flight (or vice versa), the same project paths get synced concurrently by both code paths — duplicate `GET /api/projects` calls and redundant DOM replacement. Functionally harmless (idempotent GET, `syncProject`'s own try/finally keeps `loadingProjects` consistent) but wasteful, and could cause brief UI flicker. This gap pre-dates this change (autosync already didn't coordinate with manual per-project refresh); this feature extends the same gap rather than introducing a new one.
- **Fix**: Gate both `syncAllProjects` and `autosyncAll` behind a single shared "any sync in progress" flag, only if this becomes visibly annoying in practice — not required for this change to ship.
- **Decision**: FIXED (autosyncAll now checks/sets `syncingAll`, mirroring syncAllProjects, so the two paths mutually exclude)

### F4 — Remove button stays enabled during a global sync

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: dist/app.js:300 (removeProject) / dist/app.js:339 (updateProjectUI)
- **Detail**: `updateProjectUI` disables the refresh button when `syncingAll` is true but the "Remove" button isn't covered by that guard, so a project could be deleted mid-sync. Existing null checks (`updateProjectUI` line 333, `syncProject`'s errorDiv fallback) prevent a crash — worst case is a wasted network round-trip.
- **Fix**: Extend the `syncingAll` disable guard to the Remove button as well, if it's ever observed to cause confusion.
- **Decision**: FIXED (updateProjectUI now also disables `.remove-btn` when loading or syncingAll)

### F5 — Two unplanned but benign additions

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: dist/app.js:258-262 ("No projects to sync" guard), dist/app.js:265-266/294 (`sync-all-btn` self-disable)
- **Detail**: The plan didn't itemize an empty-project-list message or disabling the "Sync All" button itself during sync (only individual refresh buttons were specified via `syncingAll`). Both are small, additive, non-conflicting improvements.
- **Fix**: No action needed — accept as implemented; optionally note in the plan as a addendum for the record.
- **Decision**: ACCEPTED (no code change needed)
