# UI Redesign (Cowork-like) Implementation Plan

## Overview

Redesign `dist/index.html` and `dist/app.js` to adopt a Claude Cowork-like aesthetic: warm neutral palette via CSS custom properties, system UI font stack, card-based layout with soft borders and shadows, and colored status badges for per-project change counts. Introduces `dist/style.css` as the single styling source of truth, replacing the current inline `<style>` block.

## Current State Analysis

The app is two files: `dist/index.html` (84 lines, one inline `<style>` block with ~8 hardcoded-hex rules) and `dist/app.js` (270 lines, imperative DOM construction). There is no color palette, type scale, spacing system, or dark-mode support — everything is browser defaults plus a handful of ad-hoc hex values. Status is communicated as a plain comma-joined text string ("2 New, 1 In Progress, 3 Done") with one bold-red inline span for blocked.

The sync path in `syncProject` (lines 147–209) duplicates the same stats-element and change-list-building logic that `renderProjectSection` (lines 43–134) already contains. The `remove-project` change (S-05) has all progress steps still unchecked — no Phase 3 ("Frontend UI") code has landed — but it will add a remove control to the same `.project-controls` area this redesign touches.

### Key Discoveries:

- `dist/index.html:20-80` — entire current inline `<style>` block; to be replaced by a `<link>` to `dist/style.css`
- `dist/app.js:43-134` — `renderProjectSection`: primary render path, the definitive source of card markup
- `dist/app.js:147-209` — `syncProject`: duplicates the stats-p and change-ul build logic; to be collapsed into a shared `buildSummaryStats` helper
- `dist/app.js:23-29` — `getStatusBucket`: maps raw statuses to `new | in_progress | done | blocked`; badge CSS class names must match these bucket strings
- `app/api.py:16-26` — `ProjectResponse` shape is the only contract that must be preserved; markup changes are fully backend-decoupled
- `tests/test_api.py`, `tests/test_changes.py`, `tests/test_projects.py` — all Python/pytest, no DOM assertions; any markup/CSS/JS change is safe

## Desired End State

`dist/` has three files: `index.html` (markup only, no inline styles), `style.css` (all visual styles via CSS custom properties), and `app.js` (logic only, emitting semantic badge markup). The page presents as a warm-neutral, card-based dashboard: a `--bg` warm off-white background, white surface cards with subtle border/shadow, system UI fonts, and colored status badges (blue/amber/green/red) replacing the plain text status line. The `syncProject` duplication is collapsed behind a shared `buildSummaryStats(aggregates)` helper. The `.project-controls` area reserves a comment-marked slot for the `remove-project` button.

### Key Discoveries:

- No build tooling anywhere in the repo; the redesign stays vanilla (no bundler/framework)
- `localStorage` key `"expanded_projects"` and the `data-project-path` attribute are behavioral — neither changes
- The `#sync-error-{path}` ID is used by `syncProject` to update error state — must remain stable or the selector updated in tandem

## What We're NOT Doing

- No dark mode / `prefers-color-scheme` support
- No web fonts via CDN — system UI font stack only
- No HTML templating engine or framework introduction
- No change-item status icons — badges on the aggregate stats line only
- No visual changes to the `remove-project` feature itself (that's S-05)
- No new API endpoints or backend changes

## Implementation Approach

Two-phase delivery: Phase 1 is pure CSS — create `style.css`, move all existing rules into it under a token-based structure, link it from `index.html`, and delete the inline `<style>` block. Zero JS changes; the page is functional throughout. Phase 2 adds the visual depth: extends `style.css` with badge, card, form, and list styles; updates `app.js` to emit badge `<span>` elements and collapses the render duplication.

---

## Phase 1: CSS Foundation & Token System

### Overview

Create `dist/style.css` with a CSS custom-property design-token system (colors, type, spacing) and global/layout styles. Update `dist/index.html` to link the new file and remove the inline `<style>` block. No JS changes.

### Changes Required:

#### 1. New file: `dist/style.css`

**File**: `dist/style.css`

**Intent**: Introduce all design tokens and global styles as the single visual source of truth, replacing the scattered hardcoded values in the inline block.

**Contract**:

`:root` must define these custom properties:

| Property | Purpose | Value |
|---|---|---|
| `--bg` | Page background | `#f8f7f4` |
| `--surface` | Card background | `#ffffff` |
| `--border` | Card/input border | `#e8e5df` |
| `--border-radius` | Consistent rounding | `8px` |
| `--accent` | Primary action color | `#c96442` |
| `--accent-hover` | Button hover | `#b3542f` |
| `--text-primary` | Main text | `#1a1a18` |
| `--text-secondary` | Muted text | `#6b6558` |
| `--text-error` | Error/destructive text | `#c62828` |
| `--font` | System UI stack | `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif` |
| `--shadow` | Card shadow | `0 1px 3px rgba(0,0,0,.08)` |

Global styles: `box-sizing: border-box`, `body` with `background: var(--bg)`, `color: var(--text-primary)`, `font-family: var(--font)`, `max-width: 800px`, `margin: 0 auto`, `padding: 2rem 1rem`.

Migrate all existing rules from the inline `<style>` block verbatim (`.refresh-btn`, `.refresh-btn:disabled`, `.refresh-btn:hover:not(:disabled)`, `.loading-indicator`, `.project-controls`, `article`, `article header`, `article h2`, `.summary-stats`, `.details`, `.details[hidden]`, `.blocked-note`, `.sync-error`) — replacing hardcoded hex values with the corresponding custom properties defined above.

#### 2. `dist/index.html`

**File**: `dist/index.html`

**Intent**: Link the new stylesheet and remove the now-redundant inline `<style>` block.

**Contract**: Add `<link rel="stylesheet" href="style.css">` inside `<head>`. Delete the entire `<style>` block (lines 20–80). No other markup changes in this phase.

### Success Criteria:

#### Automated Verification:

- `dist/style.css` exists and is non-empty
- `dist/index.html` contains `<link rel="stylesheet" href="style.css">` and does NOT contain a `<style>` tag
- Python backend tests still pass: `python -m pytest tests/ -q`

#### Manual Verification:

- Page loads in a browser without visible regressions (cards still have borders, refresh button still styled, error text still red)
- Layout is constrained to ~800px, centered on wide viewports

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation that the page renders without regression before proceeding to Phase 2. Phase blocks use plain bullets — the corresponding `- [ ]` checkboxes for these items live in the `## Progress` section at the bottom of the plan.

---

## Phase 2: Component Styles, Status Badges & JS Refactor

### Overview

Extend `dist/style.css` with Cowork-like visual polish: redesigned cards, form, and colored status badges. Update `dist/app.js` to emit badge markup instead of a plain text string, collapse the `syncProject` render duplication into a shared helper, and reserve the remove-button slot.

### Changes Required:

#### 1. `dist/style.css` — badge & component additions

**File**: `dist/style.css`

**Intent**: Add the styles that provide visual depth: card hover state, form styling, status badges, change-item list, and the empty/error note styles.

**Contract**:

Add the following rule groups (new additions, not replacements of Phase 1 rules):

- `article` upgrade: add `box-shadow: var(--shadow)`, remove the plain `border: 1px solid #ccc` in favor of `border: 1px solid var(--border)`, update `border-radius` to `var(--border-radius)`.

- `article header h2`: standalone style — `font-size: 1rem`, `font-weight: 600`, `color: var(--text-primary)`.

- `article header .project-path` (new): `font-size: 0.8rem`, `color: var(--text-secondary)`, `font-weight: 400`, displayed as a secondary line under the project name. Requires a matching markup split in app.js (see item 2 below).

- `.summary-stats`: change from `<p>` to `<div>` in app.js; add `display: flex`, `flex-wrap: wrap`, `gap: 0.4rem`, `margin: 0.4rem 0`.

- `.badge` (base): `display: inline-flex`, `align-items: center`, `padding: 2px 8px`, `border-radius: 12px`, `font-size: 0.75rem`, `font-weight: 500`.

- `.badge-new`: background `#dbeafe`, color `#1d4ed8`.
- `.badge-in-progress`: background `#fef3c7`, color `#92400e`.
- `.badge-done`: background `#dcfce7`, color `#166534`.
- `.badge-blocked`: background `#fee2e2`, color `#991b1b`.
- `.empty-note`: `font-size: 0.8rem`, `color: var(--text-secondary)`, `font-style: italic`.

- `#add-project-form`: `display: flex`, `gap: 0.5rem`, `flex-wrap: wrap`, `align-items: flex-start`, `margin-bottom: 1.5rem`.
- `#add-project-form input`: `flex: 1`, `min-width: 200px`, `padding: 0.5em 0.75em`, `border: 1px solid var(--border)`, `border-radius: var(--border-radius)`, `font: inherit`.
- `#add-project-form button`: update `background-color` to `var(--accent)`, hover to `var(--accent-hover)`.
- `#add-project-error`: `color: var(--text-error)`, `font-size: 0.875rem`.

- `.refresh-btn`: update `background-color` to `var(--accent)`, hover to `var(--accent-hover)` (replacing the blue values from Phase 1 migration).

- `.details ul`: `list-style: none`, `padding: 0`, `margin: 0`.
- `.change-item`: `padding: 0.4rem 0`, `border-bottom: 1px solid var(--border)`, `font-size: 0.875rem`, `display: flex`, `justify-content: space-between`, `gap: 0.5rem`.
- `.change-item:last-child`: `border-bottom: none`.
- `.change-item--error`: `color: var(--text-error)`.
- `.change-status`: `font-size: 0.75rem`, `color: var(--text-secondary)`, `white-space: nowrap`.

#### 2. `dist/app.js` — badge markup, shared helper & remove-button slot

**File**: `dist/app.js`

**Intent**:
a) Introduce a `buildSummaryStats(aggregates)` helper that returns a `<div class="summary-stats">` with badge `<span>` children, eliminating the duplicate stats-building logic currently in both `renderProjectSection` and `syncProject`.
b) Emit `<li class="change-item [change-item--error]">` structured list items with separate title and status spans.
c) Split the project heading into `<h2>` (name) and `<p class="project-path">` (path) for independent styling.
d) Add a comment-marked remove-button slot in `.project-controls`.

**Contract**:

New helper signature (insert near top of file, after `getAggregates`):

```js
function buildSummaryStats(aggregates) { /* returns <div class="summary-stats"> with badge spans */ }
```

Badge elements: emit a `<span class="badge badge-new">N New</span>` only when `aggregates.new > 0` (likewise for `in_progress`, `done`). Always emit the blocked badge when `aggregates.blocked > 0`. When all four counts are 0, emit `<span class="empty-note">no readable changes</span>` instead of any badge.

`renderProjectSection`: replace the current `summaryStats` build block with a call to `buildSummaryStats(aggregates)`. Split `heading.textContent = \`${project.name} (${project.path})\`` into separate `<h2>` (name only) and `<p class="project-path">` (path). Replace `summaryStats.appendChild(blockedNote)` and the `total === 0` branch (they move into `buildSummaryStats`). Add `<!-- remove-project: insert remove button here (S-05 Phase 3) -->` as the last child of the `controls` div.

`syncProject` stats update: replace the inline `newStats` build block (lines ~165–183) with `buildSummaryStats(project.aggregates)`, then `oldStats.replaceWith(newStats)`.

Change list items: replace the current single-`textContent` approach with structured markup:
- Error case: `<li class="change-item change-item--error"><span class="change-title">{change_id}: error — {error}</span></li>`
- Normal case: `<li class="change-item"><span class="change-title">{title}</span><span class="change-status">{status} · {updated}</span></li>`

Apply the same structured markup in both `renderProjectSection` and `syncProject`.

### Success Criteria:

#### Automated Verification:

- Python backend tests still pass: `python -m pytest tests/ -q`
- `dist/app.js` does NOT contain the literal string `.blocked-note` (the old class — replaced by `.badge-blocked`)
- `dist/app.js` contains `buildSummaryStats` (the new shared helper exists)

#### Manual Verification:

- Status counts appear as colored rounded badges (blue "N New", amber "N In Progress", green "N Done")
- Blocked count appears as a red badge only when present
- Projects with no readable changes show "no readable changes" in muted italic
- Add-project form is horizontally laid out and styled (input + accent-colored button)
- Expanding a project card shows change items as a clean list with title left-aligned and status/date right-aligned
- Error changes are displayed in red
- Refresh button uses the rust/orange accent color, not the old blue
- Clicking refresh still works; expand/collapse still works; add-project still works

---

## Testing Strategy

### Manual Testing Steps:

1. `python -m uv run uvicorn app.main:app --reload` and open `http://localhost:8000`
2. Verify page background is warm off-white, not bright white
3. Verify project cards have subtle shadow and rounded corners
4. Verify status badges render with correct colors per bucket
5. Add a new project — confirm form layout and error message styling
6. Expand a project card — confirm change items are list-separated with title/status/date
7. Trigger a sync on a project — confirm loading indicator still appears, error state still shows in red
8. Resize viewport narrow — confirm form wraps gracefully, cards don't overflow

## References

- Research: `context/changes/ui-improvment/research.md`
- Current markup: `dist/index.html:1-84`
- Current render logic: `dist/app.js:43-134`
- Render duplication to collapse: `dist/app.js:147-209`
- Status bucket mapping: `dist/app.js:23-29`
- remove-project coordination: `context/changes/remove-project/plan.md`

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: CSS Foundation & Token System

#### Automated

- [x] 1.1 `dist/style.css` exists and is non-empty
- [x] 1.2 `dist/index.html` contains `<link rel="stylesheet" href="style.css">` and does NOT contain a `<style>` tag
- [x] 1.3 Python backend tests pass: `python -m pytest tests/ -q`

#### Manual

- [ ] 1.4 Page loads without visible regressions (cards bordered, refresh button styled, error text red)
- [ ] 1.5 Layout constrained to ~800px, centered on wide viewports

### Phase 2: Component Styles, Status Badges & JS Refactor

#### Automated

- [ ] 2.1 Python backend tests pass: `python -m pytest tests/ -q`
- [ ] 2.2 `dist/app.js` does NOT contain `.blocked-note`
- [ ] 2.3 `dist/app.js` contains `buildSummaryStats`

#### Manual

- [ ] 2.4 Status counts appear as colored rounded badges (blue New, amber In Progress, green Done)
- [ ] 2.5 Add-project form is horizontally laid out with accent-colored button
- [ ] 2.6 Expand reveals change items with title left-aligned and status/date right-aligned
- [ ] 2.7 Refresh, expand/collapse, and add-project all work correctly end-to-end
