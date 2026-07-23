---
project: 10xDevTracker
version: 1
status: draft
created: 2026-07-23
updated: 2026-07-23
prd_version: 1
main_goal: low-complexity
top_blocker: none
---

# Roadmap: 10xDevTracker

> Derived from `context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

Solo developers using the 10xDEV framework across multiple local project directories have no central view of status — they manually open `change.md` and `plan.md` files across repos to see what's active, in-progress, or done. The app's real value isn't just aggregating files; it's that it understands the 10xDEV framework structure well enough to correctly interpret change status, phase progress, and roadmap correlation — something a generic file browser cannot do.

## North star

**S-01: Add a project path and see per-change status** — this is the smallest end-to-end slice whose successful delivery would prove the app's core hypothesis, placed as early as its Prerequisites allow because everything else only matters if this works. Here, that hypothesis is narrow and concrete: that the app can correctly parse a `context/changes/` directory and each change's `change.md` into an accurate status list, not just display raw files.

## At a glance

| ID   | Change ID                    | Outcome (user can …)                                              | Prerequisites | PRD refs             | Status   |
| ---- | ----------------------------- | ------------------------------------------------------------------ | -------------- | --------------------- | -------- |
| F-01 | minimal-web-app-scaffold      | (foundation) a running FastAPI app serves a browser-viewable page  | —              | —                     | done     |
| S-01 | project-change-status-view    | add a project path and see its changes with status                | F-01            | US-01, FR-001, FR-003 | proposed |
| S-02 | project-list-aggregate-status | see all added projects with aggregated new/in-progress/done counts | S-01            | US-01, FR-002         | proposed |
| S-03 | change-phase-progress         | see phase progress within each change (e.g. "Phase 3: 4/5")        | S-01            | US-01, FR-004         | proposed |
| S-04 | roadmap-correlation-view      | see which roadmap items each change addresses                     | S-01            | US-01, FR-005         | proposed |
| S-05 | remove-project                | remove a project from the app                                     | S-01            | FR-009                | proposed |
| S-06 | manual-single-project-sync    | manually sync a single project to refresh its status               | S-01            | FR-006                | proposed |
| S-07 | sync-all-projects             | sync all added projects at once                                    | S-02, S-06      | FR-007                | proposed |
| S-08 | configure-autosync-interval   | configure an autosync interval for automatic refreshes             | S-07            | FR-008                | proposed |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme                        | Chain                                        | Note                                                                 |
| ------ | ----------------------------- | --------------------------------------------- | --------------------------------------------------------------------- |
| A      | Core dashboard                | `F-01` → `S-01` → `S-02` → `S-03` → `S-04`   | The main data-view chain; carries the north star and its extensions. |
| B      | Project lifecycle             | `S-05`                                        | Standalone small action off `S-01`; trivial to slot in anywhere.     |
| C      | Sync automation               | `S-06` → `S-07` → `S-08`                      | Joins Stream A at `S-02` (S-07 needs the aggregate list to sync all). |

## Baseline

What's already in place in the codebase as of `2026-07-23` (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend:** absent — no frontend framework, build tooling, or `package.json` found anywhere in the repo.
- **Backend / API:** partial — FastAPI and uvicorn are declared as dependencies (`pyproject.toml:8-9`), but `main.py:1` is still a hello-world stub with no app instance or routes.
- **Data:** absent — no file-parsing logic for `change.md` / `plan.md` / `roadmap.md` exists yet.
- **Auth:** absent — and intentionally so per PRD `## Access Control`: localhost-only, no auth planned for v1.
- **Deploy / infra:** absent — no `Dockerfile`, no `.github/workflows`; deploy is explicitly deferred per `tech-stack.md`.
- **Observability:** absent — no logging/metrics/error-tracking wired.

## Foundations

### F-01: Minimal web app scaffold

- **Outcome:** (foundation) a FastAPI app instance exists, runs locally, and serves a browser-viewable page — replacing the current hello-world `main.py` stub.
- **Change ID:** minimal-web-app-scaffold
- **PRD refs:** Access Control (localhost-only, no auth), Non-Functional Requirements (local-only, no external calls)
- **Unlocks:** S-01 — no vertical slice can be user-visible until something actually runs and renders a page in a browser.
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Which frontend approach will render the page (server-rendered templates from FastAPI vs. a separate JS/TS SPA later proxied/served by FastAPI, per `tech-stack.md`'s "add a separate JS/TS frontend later")? — Owner: user. Block: no (this is a `/10x-plan`-level implementation choice, not a sequencing blocker — the roadmap doesn't need the answer to order the slices).
- **Risk:** Keeping this to "one app instance + one servable page" (not a full UI framework integration) avoids turning a foundation into a layer-completion project; the actual dashboard UI work happens inside S-01.
- **Status:** done

## Slices

### S-01: Add a project path and see per-change status

- **Outcome:** user can add a project path from the UI and see that project's changes, each with its status (new/in-progress/done), read from `change.md`.
- **Change ID:** project-change-status-view
- **PRD refs:** US-01, FR-001, FR-003
- **Prerequisites:** F-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** This is the north star — sequenced first because it proves the hardest and most valuable part (correctly parsing `change.md` into an interpreted status) with the smallest possible surface area. A wrong parsing model here would ripple into every later slice.
- **Status:** proposed

### S-02: See aggregated status across all added projects

- **Outcome:** user can view the list of added projects with aggregated status counts (e.g., "2 New, 1 In Progress, 3 Done").
- **Change ID:** project-list-aggregate-status
- **PRD refs:** US-01, FR-002
- **Prerequisites:** S-01
- **Parallel with:** S-03, S-04, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Depends only on the per-change status data S-01 already produces; aggregation is arithmetic over that, not new parsing risk. Sequenced early because sync-all (S-07) needs a project list to iterate over.
- **Status:** proposed

### S-03: See phase progress within a change

- **Outcome:** user can see phase progress within each change (current phase, tasks completed / total), read from `plan.md`.
- **Change ID:** change-phase-progress
- **PRD refs:** US-01, FR-004
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-04, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Extends the parsing model from S-01 to a second file type (`plan.md`); the main risk is `plan.md` format drift across projects, which only becomes visible once real project data is tried against it.
- **Status:** proposed

### S-04: See roadmap correlation per change

- **Outcome:** user can see which roadmap items each change addresses, correlated from `foundation/roadmap.md`.
- **Change ID:** roadmap-correlation-view
- **PRD refs:** US-01, FR-005
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-03, S-05, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Independent of S-03 (different source file, `roadmap.md` vs `plan.md`); the risk is that correlation depends on Change ID naming conventions matching between a change's `change.md` and the target project's `roadmap.md`, which this app doesn't control.
- **Status:** proposed

### S-05: Remove a project

- **Outcome:** user can remove a project from the app's tracked list.
- **Change ID:** remove-project
- **PRD refs:** FR-009
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-03, S-04, S-06
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Smallest, lowest-risk slice — a local-state removal action with no parsing involved. Sequenced wherever convenient; not on any critical path.
- **Status:** proposed

### S-06: Manually sync a single project

- **Outcome:** user can manually sync a single project to refresh its status on demand.
- **Change ID:** manual-single-project-sync
- **PRD refs:** FR-006
- **Prerequisites:** S-01
- **Parallel with:** S-02, S-03, S-04, S-05
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Re-runs the S-01 read path on demand; low risk on its own, but it's the single-project refresh mechanism that S-07 (sync all) and S-08 (autosync) both build on, so it's sequenced before them.
- **Status:** proposed

### S-07: Sync all projects at once

- **Outcome:** user can trigger a sync of all added projects in one action.
- **Change ID:** sync-all-projects
- **PRD refs:** FR-007
- **Prerequisites:** S-02, S-06
- **Parallel with:** S-03, S-04, S-05
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Needs both the project list (S-02) to know what to iterate over and the single-project sync mechanism (S-06) to reuse per project — sequenced after both rather than reimplementing either.
- **Status:** proposed

### S-08: Configure autosync interval

- **Outcome:** user can configure how often (in minutes) the app automatically refreshes project status.
- **Change ID:** configure-autosync-interval
- **PRD refs:** FR-008
- **Prerequisites:** S-07
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Autosync is sync-all on a timer; building it before sync-all exists would mean building the same iteration logic twice. Sequenced last since it's pure automation over an already-working manual sync.
- **Status:** proposed

## Backlog Handoff

| Roadmap ID | Change ID                    | Suggested issue title                                 | Ready for `/10x-plan` | Notes                              |
| ---------- | ----------------------------- | -------------------------------------------------------- | ---------------------- | ----------------------------------- |
| F-01       | minimal-web-app-scaffold      | Stand up a running FastAPI app with a servable page       | yes                    | Run `/10x-plan minimal-web-app-scaffold` |
| S-01       | project-change-status-view    | Add project path, parse `change.md`, show status list    | no                     | Depends on F-01 landing first        |
| S-02       | project-list-aggregate-status | Aggregate project list with status counts                | no                     | Depends on S-01                      |
| S-03       | change-phase-progress         | Parse `plan.md` for phase/task progress                  | no                     | Depends on S-01                      |
| S-04       | roadmap-correlation-view      | Correlate changes to `roadmap.md` items                  | no                     | Depends on S-01                      |
| S-05       | remove-project                | Remove a tracked project                                  | no                     | Depends on S-01                      |
| S-06       | manual-single-project-sync    | Manual single-project sync/refresh                        | no                     | Depends on S-01                      |
| S-07       | sync-all-projects             | Sync-all action across tracked projects                   | no                     | Depends on S-02, S-06                |
| S-08       | configure-autosync-interval   | Configurable autosync interval                            | no                     | Depends on S-07                      |

## Open Roadmap Questions

1. **Which frontend approach will render the dashboard — server-rendered templates from FastAPI, or a separate JS/TS SPA served later, as `tech-stack.md` suggests?** — Owner: user. Block: no (an implementation choice for `/10x-plan` on F-01, not a sequencing blocker for this roadmap).

## Parked

- **Autosync reliability (retry/backoff on failed syncs)** — Why parked: PRD Success Criteria "Secondary" explicitly marks autosync reliability as a v2+ feature.
- **Archive actions from the UI** — Why parked: PRD Non-Goals — "Not an orchestration tool"; the app visualizes only, archiving stays outside the app. Also listed as v2+ in Success Criteria.
- **Export (of dashboard data)** — Why parked: PRD Success Criteria "Secondary" marks export as a v2+ feature.
- **File editing from the UI** — Why parked: PRD Non-Goals — "Not a file editor"; the app is read-only by design.
- **API / MCP integration for external tools** — Why parked: PRD Non-Goals — "Not an API or MCP feature".
- **External service integrations (Slack, GitHub webhooks, Linear sync)** — Why parked: PRD Non-Goals — "Not externally integrated"; stays local and standalone.

## Done

- **F-01: (foundation) a running FastAPI app serves a browser-viewable page** — Archived 2026-07-23 → `context/archive/2026-07-23-minimal-web-app-scaffold/`. Lesson: —.
