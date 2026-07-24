# See Phase Progress Within a Change — Plan Brief

> Full plan: `context/changes/change-phase-progress/plan.md`

## What & Why

Add phase/task progress from each change's `plan.md` to the dashboard (e.g. "Phase 3: 4/5"), so a developer can see not just a change's raw status but how far along its current phase is — without opening the file. This is roadmap item S-03, the third data layer added on top of S-01's per-change status view.

## Starting Point

S-01 already parses `change.md` per change folder into a `ChangeSummary`, rendered as one `<li>` per change in the dashboard, with per-folder failure isolation so one bad file never breaks the whole project. S-02 added project-level status aggregation on top of that same data. Neither reads `plan.md` yet — this change adds that second file type.

## Desired End State

Every change row with a `plan.md` containing a populated `## Progress` section shows its current phase and step ratio inline next to its status, e.g. `Some Change [implementing] — updated 2026-07-23 — Phase 2: 2/4`. Changes with no plan yet, or an unparseable one, show nothing extra — same as today.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| What X/Y counts | Automated + Manual combined, current phase only | Matches the PRD's literal example and `progress-format.md`'s own "current phase" definition exactly. | Plan |
| All-phases-done display | Show final phase at full ratio (e.g. "Phase 3: 5/5") | Zero special-casing — one code path handles every state. | Plan |
| No-plan-yet / unparseable display | Omit silently, no error shown | Consistent with how absent/optional data already behaves elsewhere in this app. | Plan |
| UI placement | Append inline to the existing per-change text line | Smallest frontend change; consistent with how `title`/`status`/`updated` are already rendered. | Plan |
| Current-phase algorithm | First phase with an unchecked step, else last phase | Already specified verbatim in `progress-format.md`'s parsing contract — not a new invention. | Plan |

## Scope

**In scope:**
- New `app/plan_progress.py` parsing module + unit tests
- `ChangeSummary` gains a `phase_progress` field, wired in `changes.py`
- `dist/app.js` shows the phase text inline in both render paths (initial load + refresh)

**Out of scope:**
- Roadmap correlation (S-04)
- Which specific step is next, or its title
- Separate Automated vs. Manual counts in the display
- Any caching layer (matches the existing always-read-fresh design)
- Any `app/api.py` code changes (the field flows through the existing response model automatically)

## Architecture / Approach

`app/plan_progress.py` is a standalone, pure function (`Path -> PhaseProgress | None`) mirroring `app/changes.py`'s existing shape for `change.md`. `changes.py`'s existing per-folder loop in `list_changes()` calls it and attaches the result to each `ChangeSummary`. No new API routes — `ProjectResponse`'s existing `response_model` serializes the new nested field automatically. The frontend gets one template-literal edit per existing render call site.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Parsing module | `plan_progress.py` parses `## Progress` into current-phase done/total, tolerating every observed real-world edge case | `plan.md` format drift across real projects (the risk the roadmap itself flags) |
| 2. Wire into API | `ChangeSummary` + `changes.py` attach the parsed result; flows through existing endpoints untouched | Low — additive field, no endpoint changes |
| 3. Frontend | Inline text appended in both render paths (initial + refresh) | Keeping the two duplicated render paths in sync (pre-existing duplication, not introduced here) |

**Prerequisites:** S-01 (done) — this reads the same per-change folder structure it already established.
**Estimated effort:** ~1 session across 3 phases; each phase is small and follows an existing pattern closely.

## Open Risks & Assumptions

- Assumes every real `plan.md` in the wild actually follows the `progress-format.md` contract closely enough for regex-based bullet matching to work — mitigated by testing against this repo's own real, messy examples (mixed SHA-comment suffixes, single vs. multi-phase).
- If a future project's `plan.md` deviates significantly from the documented format, this parser silently shows nothing rather than erroring — consistent with the chosen "omit silently" decision, but worth knowing if phase progress mysteriously never appears for a given project.

## Success Criteria (Summary)

- A change with a real, in-progress `plan.md` (like `manual-single-project-sync`) shows its correct current-phase ratio in the dashboard.
- A change with no `plan.md` yet shows exactly what it shows today — no regression, no error noise.
- Refreshing a project updates the phase-progress text along with everything else already refreshed.
