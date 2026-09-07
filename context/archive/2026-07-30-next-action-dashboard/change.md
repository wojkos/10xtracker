---
change_id: next-action-dashboard
title: Show next recommended action prominently in the dashboard
status: archived
created: 2026-07-30
updated: 2026-09-04
archived_at: 2026-09-04T09:23:00Z
---

## Notes

Expose the existing `get_next_10x_action()` logic prominently in the dashboard — one concrete recommendation (change-id + skill command) instead of hiding it inside MCP only. Extends `workflow_recommendations.py` via a new REST endpoint.
