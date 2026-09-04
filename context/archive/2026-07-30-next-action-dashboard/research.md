# Research: next-action-dashboard

## Summary

`get_next_10x_action()` is fully implemented but exposed **only via MCP** — there is no REST endpoint and no frontend call. Adding a "Next action" panel to the dashboard requires three small steps: a new API endpoint, a new HTML section, and new JS code.

---

## Existing recommendation logic

**File:** `app/workflow_recommendations.py`

### Public API

```python
def get_next_10x_action(project_path: str | None = None) -> list[WorkflowRecommendation]:
```

- If `project_path=None` → analyzes **all** tracked projects
- Returns `list[WorkflowRecommendation]` — one entry per project

### `WorkflowRecommendation` model (line 13)

| Field | Type | Description |
|-------|------|-------------|
| `project_path` | `str` | Project root directory |
| `change_id` | `str \| None` | Active or target change |
| `command` | `str \| None` | Skill command to run (e.g. `/10x-plan feature-x`) |
| `reason` | `str` | Human-readable justification |
| `confidence` | `str` | `"high"` or `"low"` |
| `alternatives` | `list[str]` | Alternative commands |
| `candidates` | `list[str]` | Flagged change-ids when decision is blocked |
| `blocking_question` | `str \| None` | Clarification needed from user when confidence=low |

### Decision logic (lines 128–189)

1. Parse errors detected → `confidence=low`, blocked
2. Multiple active changes at once → `confidence=low`, `candidates` list returned
3. One active change → `_recommend_for_active_change()` → returns skill to run
4. No active changes → `_eligible_roadmap_change()` → proposes `/10x-new <next-slice>`

### Activity status constants (lines 8–9)

```python
ACTIVE_CHANGE_STATUSES = {"new", "preparing", "planned", "plan_reviewed", "implementing", "implemented"}
COMPLETE_ROADMAP_STATUSES = {"complete", "completed", "done"}
```

---

## Current exposure

**MCP only** — `app/mcp.py` lines 21 + 71–86:
```python
from app.workflow_recommendations import get_next_10x_action
# registered as MCP tool "get_next_10x_action"
```

**REST API** — none. `app/api.py` does not import or call `workflow_recommendations`.

---

## Frontend — dashboard structure

**Files:** `dist/index.html`, `dist/app.js` (~600 lines vanilla JS), `dist/style.css`

### HTML sections (index.html)

```
<h1>10xDevTracker</h1>
<div id="dashboard-controls">   ← autosync + sync-all
<div id="projects">             ← projects list (dynamically rendered)
<form id="add-project-form">    ← add project
```

### Data flow

```
loadProjects() → GET /api/projects → renderProjects() → DOM
```

### Existing REST endpoints (`app/api.py`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/projects` | Add project |
| GET | `/api/projects` | List projects with changes |
| DELETE | `/api/projects` | Remove project |
| GET | `/api/settings` | Get autosync settings |
| PUT | `/api/settings` | Update autosync settings |

---

## What needs to be built

### 1. New REST endpoint — `GET /api/recommendations` (`app/api.py`)

```python
@router.get("/recommendations")
def recommendations() -> list[WorkflowRecommendation]:
    return get_next_10x_action()
```

### 2. New HTML section — "Next action" panel (`dist/index.html`)

Insert **between** `#dashboard-controls` and `#projects`:

```html
<section id="next-action">
  <h2>Next action</h2>
  <div id="next-action-content"></div>
</section>
```

### 3. JS call (`dist/app.js`)

- `loadRecommendations()` → `GET /api/recommendations`
- Render: `command`, `reason`, `confidence` badge, `blocking_question` when `confidence=low`
- Call on page load (alongside `loadProjects()`) and after each sync

---

## Risks and notes

| Risk | Severity | Mitigation |
|------|----------|------------|
| `get_next_10x_action()` may be slow (reads many files) | Low — called on demand, not on every render | Call separately from `loadProjects()` |
| Recommendation may be `confidence=low` with `blocking_question` | Expected — UI must handle both states | Render `blocking_question` when non-null |
| Frontend is vanilla JS with no bundler | No change — continue that style | Add functions directly to `app.js` |

---

## Dependencies

- `app/workflow_recommendations.py` — already complete, no changes needed
- `app/api.py` — add 1 endpoint
- `dist/index.html` — add 1 section
- `dist/app.js` — add ~30–50 lines of JS
- `dist/style.css` — optional panel styling
