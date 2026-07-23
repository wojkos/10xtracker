---
name: 10xdevtracker
description: Local 10xDEV project status dashboard — FastAPI + frontend
context_type: greenfield
product_type: web-app
target_scale:
  users: small
timeline_budget:
  mvp_weeks: 3
  after_hours_only: true
  hard_deadline: null
checkpoint:
  current_phase: 8
  phases_completed: [1, 2, 3, 4, 5, 6, 7]
  frs_drafted: 9
  quality_check_status: accepted
updated: 2026-07-23
---

## Vision & Problem Statement

**Pain:** Lack of visibility into 10xDEV project status across multiple local repositories. Developers need to manually check multiple directories and files to see which changes are active, in-progress, or done.

**Moment:** When tracking progress on parallel changes, understanding roadmap status at a glance, or context-switching between projects.

**Cost today:** Manual directory navigation, no central dashboard, scattered information across multiple `change.md` and `plan.md` files.

**Insight:** The value isn't just aggregation — it's that the app understands the 10xDEV framework structure, interprets project states correctly, and visualizes how roadmap, changes, and tasks relate to each other. That's something a generic file browser can't do.

## User & Persona

**Primary persona:** Solo developer using the 10xDEV framework locally to manage multiple concurrent projects.

**Scope:** Single user, single machine, personal workflow visibility. Not multi-user or shared workspace for v1.

**What they do differently after this app ships:** Instead of navigating directories and opening multiple files to assess project status, they open a dashboard, add project paths once, and see at a glance: how many changes are new/in-progress/done, which tasks are blocking them, and what they should work on next.

## Access Control

**Authentication:** No authentication required. The app runs on `localhost` — only the developer can access it from their machine. No account creation, no login, no roles.

**Data scope:** All project paths and tracking data are stored locally on the developer's machine. No server sync, no multi-device state.

## Success Criteria

### Primary

User can add a project path from the UI, and the app reads the project's `changes/` directory and `foundation/roadmap.md`, then displays an aggregated dashboard showing:
- Per-change status (new/in-progress/done)
- Phase progress within each change (e.g., "Phase 3: 4/5 tasks completed")
- Roadmap correlation (which roadmap items each change addresses)
- Autosync capability (refresh on configurable interval)

The full flow — from first app load to seeing project status — works end-to-end.

### Secondary

None for v1. Autosync reliability, archive actions, and export are v2+ features.

### Guardrails

**Data safety:** The app reads project directories and metadata files but never modifies or deletes anything. It is read-only from the filesystem perspective.

## Timeline Acknowledgment

Acknowledged on 2026-07-23: 3-week MVP with roadmap correlation requires sustained after-hours dedication (5–7 hours/week). User explicitly accepted the sustained-effort cost and committed to this timeline.

## Functional Requirements

### Project Management

- FR-001: Developer can add a project path to the app (project directory containing context/). Priority: must-have
- FR-009: Developer can remove a project from the app. Priority: must-have

### Project Monitoring

- FR-002: Developer can view a list of added projects with aggregated status counts (new/in-progress/done). Priority: must-have
- FR-003: Developer can view changes within a project and their individual statuses (from change.md). Priority: must-have
- FR-004: Developer can view phase progress within each change (current phase, tasks completed / total). Priority: must-have
- FR-005: Developer can see which roadmap items each change addresses (roadmap correlation). Priority: must-have

### Sync & Refresh

- FR-006: Developer can manually sync a single project to refresh its status. Priority: must-have
- FR-007: Developer can sync all projects at once. Priority: must-have
- FR-008: Developer can configure autosync interval (minutes between automatic refreshes). Priority: must-have

## User Stories

### US-01: First-time project setup and dashboard view

**Given** a developer has the app running on localhost for the first time (no projects added yet)
**When** they click "Add project" and paste a path to a 10xDEV project directory (e.g., `D:\trinity\trinity-core\context`)
**Then** the app reads the directory, extracts changes and roadmap data, and displays a dashboard showing:
- All projects in the list with aggregated status (e.g., "2 New, 1 In Progress, 3 Done")
- Each change with its status from change.md
- Each change's current phase and task progress (e.g., "Phase 3: 4/5")
- Correlation between changes and roadmap items
- Sync and autosync options visible and ready to use

### Socrates Round: All FRs Reviewed

All 9 FRs passed Socrates challenge. Each was considered against plausible counter-arguments (auto-discovery vs manual paths, aggregation vs raw lists, phase detail vs simplification, etc.) and each stood as written. Scope is validated.

## Business Logic

**Rule of operation:** The app aggregates distributed 10xDEV project metadata (changes, roadmap, plan files) and surfaces them as a unified, framework-aware status dashboard.

**Inputs:** The developer provides a project directory path (containing a `context/` subdirectory with 10xDEV structure). The app reads:
- `changes/` directory (all change folders)
- `change.md` files (per change, to extract status)
- `plan.md` files (per change, to extract phase and task data)
- `foundation/roadmap.md` (to correlate changes to roadmap items)

**Output:** A dashboard displaying aggregated status (counts by new/in-progress/done), per-change phase progress, and roadmap correlation — all derived from the metadata without modification.

**User encounters it:** Developer adds a project path via UI → app reads metadata → dashboard appears immediately with full status visible.

## Non-Functional Requirements

No explicit commitments for v1. Sensible defaults apply: local storage only (no external calls), desktop-browser focused, performance optimized for typical project counts (1–10 projects, 20–50 changes per project).

## Non-Goals

- **Not a file editor:** The app is read-only. No creation, modification, or deletion of project files from the UI. Changes to projects happen outside the app.
- **Not an API or MCP feature:** The app does not expose an API, plugin interface, or MCP integration for external tools to consume.
- **Not an orchestration tool:** The app does not trigger actions (archiving, creating changes, updating status). It visualizes only; users manage projects outside the app.
- **Not externally integrated:** No Slack notifications, GitHub webhooks, Linear syncs, or external service integrations. Stays local and standalone.

