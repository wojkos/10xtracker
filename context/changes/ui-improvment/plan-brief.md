# UI Redesign (Cowork-like) — Plan Brief

> Full plan: `context/changes/ui-improvment/plan.md`
> Research: `context/changes/ui-improvment/research.md`

## What & Why

The app's current UI is unstyled browser defaults plus a handful of hardcoded hex values — no design tokens, no type scale, no visual hierarchy. This change introduces a Claude Cowork-like aesthetic (warm neutral palette, card-based layout, colored status badges) to make the dashboard feel polished and readable rather than a functional prototype.

## Starting Point

Two files: `dist/index.html` (84 lines, one inline `<style>` block with ~8 rules) and `dist/app.js` (270 lines, imperative DOM construction). Status counts are rendered as plain comma-joined text. No CSS custom properties, no font declaration, no design system of any kind.

## Desired End State

Three files in `dist/`: `index.html` (markup only, no inline styles), `style.css` (all visual styles via CSS custom properties), and `app.js` (logic only, emitting semantic badge markup). The page presents as a warm-neutral dashboard with white cards, subtle shadows, system UI fonts, and colored status badges (blue/amber/green/red) replacing the plain text status line. The `syncProject` render duplication is eliminated.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| CSS location | External `dist/style.css` | Clean separation; token-based system needs its own file | Plan |
| Fonts | System UI font stack | No CDN dependency, zero latency, consistent with no-build-tooling posture | Plan |
| Status visualization | Colored badge `<span>` elements | Biggest visual upgrade, at-a-glance readability, Cowork-like aesthetic | Plan |
| remove-project coord. | Reserve a comment slot | Avoids guaranteed conflict when S-05 Phase 3 lands | Plan |
| Render duplication | Collapse via `buildSummaryStats` helper | Natural seam exposed by the badge refactor; no extra cost | Research |
| Build tooling | Stay vanilla | Repo explicitly resolved this in roadmap; no `package.json` anywhere | Research |

## Scope

**In scope:**
- `dist/style.css` (new file) — all design tokens and component styles
- `dist/index.html` — remove inline `<style>`, add `<link>`, no other markup changes in Phase 1
- `dist/app.js` — badge markup, structured change-item markup, `buildSummaryStats` helper, remove-button slot comment

**Out of scope:**
- Dark mode / `prefers-color-scheme`
- Web fonts / CDN dependencies
- Any frontend framework or build tooling
- Status icons on change list items
- Backend changes

## Architecture / Approach

Token-first, two-phase delivery. Phase 1 is purely additive and CSS-only — create `style.css`, migrate existing rules under named tokens, link from `index.html`. The page is functional throughout and this phase can be verified independently. Phase 2 adds the visual depth and JS refactoring: badge markup, card/form polish, change-item structured layout, and duplication collapse. Keeping the phases separate means a mid-work pause is safe.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. CSS Foundation & Token System | `dist/style.css` with design tokens; `index.html` links it; no regressions | Forgetting to migrate a rule from the inline block |
| 2. Component Styles, Badges & JS Refactor | Colored badges, styled cards/form/list; collapsed render duplication | Badge class names must match `getStatusBucket` bucket strings exactly |

**Prerequisites:** None — both dist files exist and the backend is already running  
**Estimated effort:** ~1-2 sessions across 2 phases

## Open Risks & Assumptions

- The `remove-project` Phase 3 (S-05) will still require manual reconciliation when it lands, even with the comment slot — the implementer must wire up the button into the reserved area
- "Cowork-like" palette is interpreted from general knowledge of Anthropic's design language, not a pixel-accurate spec; the warm neutral + rust/orange accent may need tuning after first visual review

## Success Criteria (Summary)

- Status counts render as colored rounded badges with correct bucket colors (blue, amber, green, red)
- Page background, cards, form, and list items all reflect the warm neutral palette with system UI fonts
- All existing backend tests pass and all interactive features (add, expand, refresh) work correctly end-to-end
