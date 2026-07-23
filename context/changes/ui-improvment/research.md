---
date: 2026-07-23T14:59:58+02:00
researcher: Wojciech Kostanski
git_commit: e09d34cf4beb64504d11379167a510218585d48d
branch: master
repository: 10xtracker
topic: "Redesign the dashboard UI to look like Claude Cowork"
tags: [research, codebase, frontend, ui, design-system, dist-app-js, index-html]
status: complete
last_updated: 2026-07-23
last_updated_by: Wojciech Kostanski
---

# Research: Redesign the dashboard UI to look like Claude Cowork

**Date**: 2026-07-23T14:59:58+02:00
**Researcher**: Wojciech Kostanski
**Git Commit**: e09d34cf4beb64504d11379167a510218585d48d
**Branch**: master
**Repository**: 10xtracker

## Research Question

"improve ui look — I would like the app to look like Claude Cowork"

## Summary

The app is a single unstyled HTML page ([dist/index.html](dist/index.html)) plus one vanilla-JS file ([dist/app.js](dist/app.js)) — 354 lines total, no framework, no bundler, no `package.json` anywhere in the repo. Styling today is limited to one inline `<style>` block covering ~8 classes (a blue refresh button, error/loading text colors, a bordered `article` card, a "blocked" red note); everything else (`h1`, `p`, `form`, default text) is unstyled browser defaults. There is no color palette, type scale, spacing system, or dark-mode support to build on — a Cowork-like look means introducing all of that from scratch, not adjusting an existing design system.

The good news: the surface area is genuinely small (one HTML file, one JS file, ~10 DOM-producing functions), there are **no frontend tests** (only backend Python tests under `tests/`, none touch the DOM), and the backend contract (`/api/projects` GET/POST) is completely decoupled from how the frontend renders it — so the redesign has full freedom to restructure markup/CSS/JS without needing backend changes.

The one real coordination risk: **`remove-project` (S-05)** is mid-plan (`status: implementing`) and its unstarted Phase 3 ("Frontend UI") will add a remove control into the same `article header .project-controls` markup this redesign will restyle. See [Historical Context](#historical-context-from-prior-changes) and [Open Questions](#open-questions).

I was not given a Cowork screenshot/URL, so "look like Cowork" is interpreted from general knowledge of Anthropic's product design language (warm neutral background, muted rust/orange accent, soft rounded cards with subtle borders/shadows, clear serif/sans type hierarchy, generous whitespace, light+dark parity) rather than a pixel-accurate spec. I attempted to ask clarifying questions about scope/depth/tech-constraint/theming via `AskUserQuestion`; they went unanswered, so the assumptions below are explicit defaults, not confirmed decisions — flag them before `/10x-plan` locks anything down.

## Detailed Findings

### Frontend structure (all of it)

- [dist/index.html](dist/index.html) — 84 lines. Single page: `<h1>`, one `<p>`, an "add project" `<form>` (path input + submit button + inline error `<p>`), an empty `#projects` container the JS fills in, and one inline `<style>` block (lines 20-80). Script tag loads `app.js` (line 82).
- [dist/app.js](dist/app.js) — 270 lines, no imports/exports, runs as a classic script. Structure:
  - Module state: `loadingProjects` (Set, tracks in-flight refreshes) and `expandedState` (object, persisted to `localStorage` under key `expanded_projects`) — [dist/app.js:1-2](dist/app.js:1-2).
  - `getStatusBucket(status)` maps the 7 raw change statuses (`new`, `preparing`, `planned`, `plan_reviewed`, `implementing`, `implemented`, `impl_reviewed`, `archived`, `blocked`) into 4 UI buckets: `new`, `in_progress`, `done`, `blocked` — [dist/app.js:23-29](dist/app.js:23-29).
  - `getAggregates(changes)` counts changes per bucket, skipping any change with a parse `error` — [dist/app.js:31-41](dist/app.js:31-41).
  - `renderProjectSection(project)` builds one `<article>` per project imperatively via `document.createElement` (no templating engine): header with `<h2>` name+path, summary stats `<p>` ("N New, N In Progress, N Done" + optional blocked note + optional "no readable changes" note), a controls div (Refresh button + loading indicator), and a collapsible `.details` div containing a `<ul>` of per-change `<li>` rows — [dist/app.js:43-134](dist/app.js:43-134).
  - Click-to-expand/collapse on the header (guarded so clicking the controls doesn't toggle) persists to `expandedState`/localStorage — [dist/app.js:120-131](dist/app.js:120-131).
  - `syncProject(projectPath)` re-fetches `/api/projects`, finds the matching project, and **manually rebuilds** the stats `<p>` and change `<ul>` in place (duplicating the same markup-building logic from `renderProjectSection`) — [dist/app.js:147-209](dist/app.js:147-209). This duplication is a natural seam to collapse into one render function while touching this file for a redesign.
  - `updateProjectUI(projectPath)` toggles the refresh button's disabled state and loading-indicator visibility — [dist/app.js:211-221](dist/app.js:211-221).
  - `DOMContentLoaded` handler wires initial load, applies persisted expand/collapse state, and handles the add-project form submit (POST, re-render, re-apply expand state) — [dist/app.js:241-270](dist/app.js:241-270).

### Backend / data contract (frontend-agnostic, no changes needed for a pure UI redesign)

- [app/main.py](app/main.py) — `FastAPI()` app, mounts `api.router` under `/api`, serves the `dist/` directory as the frontend via `app.frontend("/", directory="dist")` (FastAPI 0.139.2 built-in SPA-serving helper — confirmed present via `uv run python -c "hasattr(fastapi.FastAPI, 'frontend')"` → `True`).
- [app/api.py](app/api.py) — `GET /api/projects` and `POST /api/projects` (add), both returning `ProjectResponse { path, name, changes: ChangeSummary[] }` — [app/api.py:16-26](app/api.py:16-26). No `DELETE` yet (that's `remove-project`, still unimplemented).
- [app/changes.py](app/changes.py) — `ChangeSummary { change_id, title, status, updated, error? }`, parsed from each project's `context/changes/*/change.md` frontmatter — [app/changes.py:9-15](app/changes.py:9-15). A change with `error` set (missing/malformed frontmatter) renders as `"{change_id}: error — {error}"` in the list today ([dist/app.js:106-108](dist/app.js:106-108)) — a redesign should keep a visually distinct (not just plain-text) error state.
- [app/projects.py](app/projects.py) — tracked-project list persisted to `data/tracked_projects.json`; a path is only accepted if it has a `context/changes/` directory ([app/projects.py:7-10](app/projects.py:7-10)). Not relevant to visual redesign beyond knowing the "add project" error path (400 response, shown in `#add-project-error`).

### Design-system gaps relative to a Cowork-like look

- No CSS custom properties / theme tokens anywhere — every color is a hardcoded hex (`#1976d2`, `#d32f2f`, `#ccc`, `#555`) inline in `index.html`'s `<style>` block ([dist/index.html:20-80](dist/index.html:20-80)).
- No font-family declaration at all — renders in the browser's default serif/sans, no type scale (h1/h2/body all default sizes except the few classes with explicit `font-size`).
- No spacing scale — margins/padding are ad hoc `0.5em`/`1em` values per element.
- Status is currently communicated as plain comma-joined text ("2 New, 1 In Progress, 3 Done") plus one bold-red inline span for "blocked" — no colored pills/badges, no icons.
- No dark mode / `prefers-color-scheme` handling anywhere.
- Layout is a single vertical column (form, then stacked project `<article>` cards) — no sidebar, no multi-pane structure.

### Testing surface (constrains what's safe to change)

- `tests/test_api.py`, `tests/test_changes.py`, `tests/test_projects.py` — all backend Python/pytest, exercising `app/api.py`, `app/changes.py`, `app/projects.py` directly. None instantiate a browser or assert on HTML/DOM structure, element IDs, or CSS classes.
- **Implication:** a UI redesign can freely change `dist/index.html` markup, `dist/app.js` structure, element IDs/classes, and add new CSS files without breaking any existing test. The only contract that must be preserved is the `/api/projects` JSON shape consumed by `app.js`.

## Code References

- `dist/index.html:1-84` — entire current markup + inline styles
- `dist/app.js:1-270` — entire current frontend logic
- `dist/app.js:23-29` — status-to-bucket mapping (source of truth for what "New/In Progress/Done/Blocked" badges must represent)
- `dist/app.js:43-134` — primary render function (card/article structure to restyle)
- `dist/app.js:147-209` — duplicate render logic in the sync path (refactor opportunity while touching this file)
- `app/main.py:7` — `app.frontend("/", directory="dist")`, how `dist/` gets served
- `app/api.py:16-26` — `ProjectResponse` schema (frontend's data contract)
- `app/changes.py:9-15` — `ChangeSummary` schema, including the `error` field's plain-text rendering today

## Architecture Insights

- **No build step by design.** The roadmap's `## Baseline` explicitly notes "Frontend: absent — no frontend framework, build tooling, or `package.json` found anywhere in the repo" (`context/foundation/roadmap.md`), and its one open question ("server-rendered templates vs. separate JS/TS SPA") was resolved in practice by shipping plain HTML+JS served via FastAPI's `.frontend()` helper — not a framework. A redesign that stays vanilla is consistent with everything decided so far; introducing a bundler/framework would be a first for this repo.
- **Imperative DOM construction, no templating.** Every element is built with `document.createElement` + manual attribute/text assignment. A visual redesign is pure CSS/markup work layered onto this same pattern — it doesn't require adopting a templating approach, though the render-duplication noted above ([dist/app.js:147-209](dist/app.js:147-209)) is worth collapsing into a shared function regardless of visual changes.
- **State is minimal and localStorage-backed.** Only `expandedState` persists (which project cards are expanded) — no other client-side state to worry about breaking during a restyle.

## Historical Context (from prior changes)

- `context/changes/project-list-aggregate-status/change.md` (S-02, **implemented**) — introduced the aggregate counts and collapsible per-project detail view that `renderProjectSection`/`syncProject` implement today. This is the most recent UI-shaping change and the direct ancestor of the markup being redesigned.
- `context/changes/manual-single-project-sync/change.md` (S-06, **implemented**) — added the Refresh button + loading indicator + `.sync-error` div now sitting in `.project-controls`.
- `context/changes/remove-project/change.md` (S-05, **status: implementing**, but `context/changes/remove-project/plan.md`'s `## Progress` section shows **all steps still unchecked** — no code has actually landed for it yet). Its Phase 3 is "Frontend UI" and will add a remove control into the same header/`.project-controls` area this redesign touches. **This is a live sequencing conflict**: if both changes land independently, whichever merges second will likely need to reconcile markup in the same region.
- `context/archive/2026-07-23-project-change-status-view/` (S-01, archived) — origin of the base per-change list markup (`{title} [{status}] — updated {updated}`) still used verbatim today ([dist/app.js:107-108](dist/app.js:107-108)).
- `context/foundation/roadmap.md` — `## Baseline` and `## Open Roadmap Questions` sections, referenced above, establish that vanilla/no-build-tooling is the accepted status quo, not an oversight.

## Related Research

None — no other `research.md` exists yet under `context/changes/**/` or `context/archive/**/` (only `plan.md`/`plan-brief.md`/`change.md` artifacts).

## Open Questions

The scoping questions asked via `AskUserQuestion` at the start of this research went unanswered. Recorded here as explicit assumptions/defaults for `/10x-plan` (or `/10x-frame`, if the framing itself needs challenging first) to confirm or override before implementation:

1. **Visual reference is inferred, not confirmed.** No Cowork screenshot/URL was supplied. "Cowork-like" is being interpreted as: warm neutral background, muted accent color, soft rounded cards with subtle border/shadow, clear typographic hierarchy, generous whitespace, light+dark parity. If the user has a specific screenshot or a more precise reference in mind, that should be captured before `/10x-plan` fixes exact colors/type.
2. **Assumed focus (all four traits)**: layout structure, color/theme, typography, and status badge/card styling are all in scope, rather than a narrower subset.
3. **Assumed depth: cosmetic refresh**, i.e. keep the current single-column structure (form on top, stacked project cards below) and restyle it, rather than a structural redesign (e.g., sidebar navigation, separate list/detail views). A structural redesign is a materially larger change and should be an explicit choice, not a default.
4. **Assumed tech constraint: stay vanilla HTML/CSS/JS**, no build tooling or framework — consistent with the roadmap baseline and the absence of any `package.json` in the repo today.
5. **Assumed theming: light + dark mode**, since Cowork supports both and CSS custom properties make this low-incremental-cost once a token system exists — but this could be descoped to light-only if the user wants a smaller first pass.
6. **Sequencing with `remove-project` (S-05)**: should this UI redesign land before or after `remove-project`'s Phase 3 frontend work, or should the two be coordinated (e.g., redesign lands first and `remove-project`'s plan gets a small update to target the new markup)? Unresolved — worth deciding at `/10x-plan` time.
