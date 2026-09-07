# Next Action Dashboard Panel — Plan Brief

> Full plan: `context/changes/next-action-dashboard/plan.md`
> Research: `context/changes/next-action-dashboard/research.md`

## What & Why

We are exposing the existing workflow recommendation engine in the web dashboard so users can immediately see what to do next without switching to MCP tooling. The goal is to make one concrete next-step command visible, actionable, and current after normal dashboard operations.

## Starting Point

Recommendation logic already exists in backend code (`get_next_10x_action`) and is tested, but it is only surfaced via MCP. The dashboard currently renders projects and sync state, with no recommendation panel or `/api/recommendations` endpoint.

## Desired End State

The dashboard includes a "Next action" panel that displays one recommendation per tracked project, including command/reason for high confidence and blocking details for low confidence. Recommendations refresh automatically after state-changing actions (add/remove/sync/sync-all/autosync), so guidance stays aligned with current project metadata.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| Panel scope | One recommendation per project | Preserves full `get_next_10x_action()` output and avoids lossy global aggregation. | Research + Plan |
| Low-confidence UX | Show reason + blocking question + candidates | Ambiguous states must remain actionable instead of being hidden. | Plan |
| Refresh strategy | Initial load + all state-changing flows | Recommendation state can change after sync/add/remove, so panel must refresh with lifecycle events. | Plan |
| Backend exposure | Add `GET /api/recommendations` | Reuses existing recommendation logic with minimal new surface area. | Research |
| Architecture boundary | Keep recommendation logic unchanged | Existing decision engine is already complete; this change is exposure + UX only. | Research + Plan |

## Scope

In scope:
- New REST endpoint: `GET /api/recommendations`
- Dashboard "Next action" panel in `dist/index.html`
- Frontend fetch/render logic in `dist/app.js`
- Panel styling in `dist/style.css`
- API tests for endpoint response behavior

Out of scope:
- Changes to recommendation decision rules
- Command-run/copy interactions in UI
- Recommendation filtering/searching
- Persistence/caching or migration work

## Architecture / Approach

Add a thin API layer in `app/api.py` that returns `WorkflowRecommendation` models from existing backend logic. Then add a dashboard panel and a dedicated `loadRecommendations()` frontend path that renders confidence-aware recommendation cards. Finally, wire recommendation reloads into existing lifecycle hooks so this new UI remains fresh without changing core project-loading architecture.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Add Recommendations API Endpoint | Typed `/api/recommendations` route with test coverage | Missing edge-case fixtures could under-test low-confidence payloads |
| 2. Add Next Action Panel Rendering | New panel + confidence-aware renderer in dashboard | Rendering can become noisy if low-confidence details are not formatted clearly |
| 3. Wire Recommendation Refresh Lifecycle | Recommendation refresh after initial load and sync/add/remove/autosync flows | Duplicate or missed refresh hooks can leave stale recommendations |

Prerequisites: Existing recommendation logic remains stable in `app/workflow_recommendations.py`; dashboard static files are served from `dist/`.
Estimated effort: ~2-3 sessions across 3 phases.

## Open Risks & Assumptions

- Assumes recommendation generation latency remains acceptable when called after frequent sync actions.
- Assumes one recommendation per tracked project remains readable at expected project counts.
- Assumes lifecycle hooks can be added without introducing UI race conditions between project and recommendation refreshes.

## Success Criteria (Summary)

- Dashboard visibly shows next action recommendations for tracked projects, including actionable low-confidence guidance.
- Recommendations update after add/remove/sync/sync-all/autosync without manual page reload.
- Existing project/sync functionality remains intact while new endpoint and panel behavior are verified by tests and manual checks.
