# App as MCP Implementation Plan

## Overview

Expose 10xDevTracker as a desktop-local, read-only MCP server for VS Code / GitHub Copilot. The server will provide tracked-project status, recently updated change records, and conservative next 10x workflow recommendations through the official Python MCP SDK, while FastAPI remains the application host.

## Current State Analysis

The FastAPI app currently serves REST endpoints and the frontend from a single application instance. Its REST adapter already aggregates tracked projects and parsed change metadata, including plan progress and basic roadmap correlation. The data layer is read-only for the information this MCP release needs, but no shared status service, recent-work ordering, workflow recommendation engine, MCP protocol adapter, or authentication boundary exists.

The roadmap parser only retains an ID and outcome today, so it cannot determine whether roadmap prerequisites are met. The new recommendation behavior must add that domain information and refuse to choose when multiple active changes or untrustworthy artifacts leave the next action ambiguous.

## Desired End State

When started on `127.0.0.1` with `MCP_AUTH_TOKEN` set, 10xDevTracker accepts authenticated MCP Streamable HTTP requests at `/mcp` from VS Code / GitHub Copilot. The agent can discover and call three read-only tools:

- `get_project_status` reports the same parsed, tracked-project aggregate available through REST.
- `get_recent_work` reports recently updated change records with explicit parse errors and a documented file-update interpretation.
- `get_next_10x_action` recommends an eligible workflow command only when the project state supports a safe choice; otherwise it returns structured candidates or a blocking question.

Unauthenticated calls are rejected before MCP dispatch, absent configuration fails closed, and no tool expands access beyond the persisted tracked-project list.

### Key Discoveries:

- The existing REST aggregation is private to [app/api.py](app/api.py#L28-L50), so a public shared status service is needed before the MCP adapter can reuse it cleanly.
- [app/changes.py](app/changes.py#L58-L75) already produces read-only change summaries containing parse errors, plan progress, and roadmap correlation; those errors must remain data in MCP responses.
- [app/plan_progress.py](app/plan_progress.py#L42-L67) identifies the first incomplete phase, while the current roadmap model in [app/roadmap_correlation.py](app/roadmap_correlation.py#L5-L42) omits prerequisite and status data needed to select an eligible new slice.
- [app/main.py](app/main.py#L1-L7) is the host integration point, and [tests/test_api.py](tests/test_api.py#L1-L19) establishes the `TestClient` and temporary-data-file test pattern.

## What We're NOT Doing

- Exposing MCP tools that add, remove, edit, sync, archive, or otherwise mutate projects and files.
- Supporting arbitrary filesystem paths: all tools operate over persisted tracked projects only.
- Hand-rolling JSON-RPC, MCP initialization, tool dispatch, or session handling.
- Using FastMCP instead of the official Python MCP SDK.
- Providing a remote deployment, multi-user authorization design, audit trail, dynamic secret reload, or configuration-backed secret storage.
- Treating `updated` frontmatter as an event/audit history rather than the timestamp of a change record update.

## Implementation Approach

Keep FastAPI as the application boundary and use the official Python MCP SDK solely for MCP protocol and Streamable HTTP behavior. Extract REST-owned status aggregation into a read-only domain service used by both adapters. Place recent-work ordering and workflow recommendation logic in dedicated domain modules, preserve existing parser failures as structured output, and keep the MCP module responsible only for startup configuration, constant-time Bearer-token validation, SDK wiring, and tool-to-service adaptation.

## Critical Implementation Details

Capture and validate `MCP_AUTH_TOKEN` during application setup so an unset or empty token prevents MCP dispatch; token rotation is intentionally a server-restart operation. Authenticate every request before the MCP SDK sees JSON-RPC content, compare the supplied bearer token with `hmac.compare_digest`, and never log the header or secret.

## Phase 1: Shared Read Models and Workflow Decisions

### Overview

Create reusable, read-only application services that give REST and MCP the same project-status view, expose well-defined recent-work ordering, retain roadmap dependency state, and make conservative workflow recommendations.

### Changes Required:

#### 1. Shared project status service

**Files**: `app/project_status.py`, [app/api.py](app/api.py#L28-L50)

**Intent**: Move tracked-project aggregation out of the REST-private helper so REST and MCP return the same project path, name, and parsed change data without importing an underscore-prefixed adapter helper.

**Contract**: Provide a public read-only function that returns the existing project response model for every path from `load_tracked_projects()`. REST `POST /api/projects` continues to validate and add a path, then serializes that one project's status through the same service boundary.

#### 2. Roadmap metadata and eligibility parsing

**Files**: [app/roadmap_correlation.py](app/roadmap_correlation.py#L5-L42), `tests/test_roadmap_correlation.py`

**Intent**: Expand the roadmap read model beyond correlation so a recommendation can identify declared status, prerequisites, and roadmap order without reparsing markdown elsewhere.

**Contract**: Parse valid rows from the existing `## At a glance` table into structured records keyed by change ID, preserving roadmap ID, outcome, prerequisites, status, and table order. Treat `-`/`—` as no prerequisites; malformed or missing table data must yield an unavailable/ambiguous recommendation rather than a guessed eligible slice.

#### 3. Recent-work and workflow recommendation services

**Files**: `app/recent_work.py`, `app/workflow_recommendations.py`, `tests/test_recent_work.py`, `tests/test_workflow_recommendations.py`

**Intent**: Give MCP stable structured outputs for recent records and next-step guidance while keeping policy separate from file parsers and protocol code.

**Contract**: `get_recent_work(limit=10)` operates solely over tracked projects, sorts valid ISO `updated` values descending, places invalid or missing values after dated records, validates a bounded positive limit, and returns project identity plus each existing change summary. Workflow recommendations return `project_path`, `change_id` when known, `command` when safe, `reason`, `confidence`, `alternatives` where applicable, and `blocking_question` when no command is safe.

Implement these deterministic rules:

- For zero active changes, select only the earliest roadmap row whose status is not complete and whose prerequisites are complete; recommend `/10x-new <change-id>`. If no row can be proven eligible, return no command and explain why.
- For one active `new` change without research or frame context, recommend `/10x-research <change-id>`; frame remains an optional response to an ambiguous problem statement rather than an automatic prerequisite.
- For a `new` or `preparing` change with research or frame context but no plan, recommend `/10x-plan <change-id>`.
- For a `planned` change without a plan review artifact, recommend `/10x-plan-review <change-id>`.
- For an implementation-ready change with unchecked plan-progress items, recommend `/10x-implement <change-id> phase <n>` and identify the first incomplete phase; list `/10x-tdd`, `/10x-e2e`, and `/10x-goal-implement` only as caller-selected alternatives when their preconditions are applicable.
- For a fully checked plan, recommend `/10x-impl-review <change-id>` and name `/10x-archive <change-id>` as the follow-up after review.
- For multiple active changes, conflicting artifacts, missing required evidence, malformed records, or unsupported lifecycle values, return candidates or a blocking question with no command.

### Success Criteria:

#### Automated Verification:

- New project-status service tests prove REST and service output use the same parsed aggregate: `python -m uv run pytest tests/test_api.py -q`
- Roadmap parser tests cover prerequisites, status, ordering, absent tables, and malformed rows: `python -m uv run pytest tests/test_roadmap_correlation.py -q`
- Recent-work tests cover ordering, invalid dates, limits, and tracked-project-only scope: `python -m uv run pytest tests/test_recent_work.py -q`
- Workflow tests cover every recommendation rule, eligible prerequisites, multiple-active-change ambiguity, and malformed-state blocking: `python -m uv run pytest tests/test_workflow_recommendations.py -q`

#### Manual Verification:

- Inspect a fixture project with malformed `change.md` data and confirm valid records remain visible while the malformed record retains an explicit diagnostic.
- Inspect a project with multiple active changes and confirm the service returns candidates without selecting a command.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Authenticated MCP Transport

### Overview

Add official MCP SDK-backed Streamable HTTP transport to the FastAPI application and register read-only MCP tools over the Phase 1 services.

### Changes Required:

#### 1. MCP dependency and adapter

**Files**: [pyproject.toml](pyproject.toml#L1-L17), `app/mcp.py`, [app/main.py](app/main.py#L1-L7)

**Intent**: Add the official Python MCP SDK and mount its Streamable HTTP integration at `/mcp` while preserving the existing `/api` router and frontend host.

**Contract**: The MCP SDK owns `initialize`, tool discovery, tool calls, JSON-RPC validation, and session behavior. FastAPI mounts exactly one `POST /mcp` Streamable HTTP endpoint; no bespoke REST invocation endpoint is introduced. The app remains launched on `127.0.0.1` for the supported desktop-local deployment.

#### 2. Authentication boundary

**Files**: `app/mcp.py`, `tests/test_mcp.py`

**Intent**: Restrict every MCP protocol request to a desktop agent configured with the same manually generated environment secret.

**Contract**: Read `MCP_AUTH_TOKEN` at application setup, reject unset/empty configuration with a clear fail-closed application error, require `Authorization: Bearer <token>` for every MCP request, and return HTTP 401 for missing, malformed, or incorrect credentials before tool dispatch. Use `hmac.compare_digest` for the secret comparison and do not expose or log token values. A changed environment token requires a server restart.

#### 3. Read-only MCP tool contracts

**Files**: `app/mcp.py`, `tests/test_mcp.py`

**Intent**: Register discoverable MCP tools that adapt the shared services into agent-friendly structured responses without creating parallel business logic.

**Contract**: Expose `get_project_status`, `get_recent_work`, and `get_next_10x_action`. Each tool reads only the persisted tracked-project list. Status output matches the REST aggregate; recent-work output labels its timestamp as record-update data; recommendation output preserves candidate and blocking-question fields. Per-record parser errors are returned as data rather than converted to an MCP protocol error.

### Success Criteria:

#### Automated Verification:

- Dependency resolution and application import succeed: `python -m uv run python -c "import app.main"`
- MCP tests reject missing, malformed, and invalid Bearer tokens before tool dispatch: `python -m uv run pytest tests/test_mcp.py -q`
- MCP protocol tests exercise initialization, `tools/list`, and each `tools/call` contract with a configured token: `python -m uv run pytest tests/test_mcp.py -q`
- The full test suite passes: `python -m uv run pytest -q`

#### Manual Verification:

- Start the server with a generated token on `127.0.0.1` and confirm an unauthenticated HTTP request to `/mcp` returns 401 without protocol output.
- Use VS Code / GitHub Copilot's configured MCP client to discover all three tools and invoke them against a tracked fixture or local project.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: VS Code Setup and Operational Documentation

### Overview

Document the supported local deployment and desktop-client setup so the MCP server can be configured safely and verified without guessing about token scope or transport behavior.

### Changes Required:

#### 1. Local launch and security documentation

**Files**: [README.md](README.md#L1-L9)

**Intent**: Extend the runtime documentation with repeatable MCP setup, bind behavior, environment-secret generation, and rotation expectations.

**Contract**: Standardize commands on `python -m uv`, demonstrate generation of a token without committing it, set `MCP_AUTH_TOKEN` only in the process environment, require Uvicorn `--host 127.0.0.1`, and state that token rotation requires a restart. Retain the existing browser-app launch information.

#### 2. VS Code / GitHub Copilot MCP configuration guidance

**Files**: [README.md](README.md#L1-L9)

**Intent**: Provide the exact supported client integration path and a concise post-setup verification procedure.

**Contract**: Include a VS Code/GitHub Copilot MCP server configuration example for authenticated Streamable HTTP at `http://127.0.0.1:8000/mcp`, with the token sourced from supported local configuration rather than written into tracked project files. Identify `get_project_status`, `get_recent_work`, and `get_next_10x_action` as read-only tools and document their scope as persisted tracked projects.

### Success Criteria:

#### Automated Verification:

- README commands use the repository-standard `python -m uv` invocation: `rg "uv run" README.md` returns no matches
- The full test suite still passes after documentation and final integration work: `python -m uv run pytest -q`

#### Manual Verification:

- Follow the README in a fresh PowerShell session to generate a token, launch the loopback-bound app, and configure VS Code / GitHub Copilot without placing the secret in version control.
- Discover and call each documented tool in VS Code / GitHub Copilot, then rotate the token and confirm that restarting the server is required before the new token works.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before declaring the change complete.

---

## Testing Strategy

### Unit Tests:

- Shared project-status aggregation stays equivalent to the REST project representation.
- Roadmap parser retains prerequisites, status, and order while tolerating absent/malformed rows.
- Recent-work parsing validates limits, date ordering, invalid dates, and tracked-project-only selection.
- Workflow recommendation rules cover active-change lifecycle, missing artifacts, first incomplete phase, completed plans, eligible roadmap slices, and all ambiguous states.

### Integration Tests:

- FastAPI TestClient confirms MCP authentication is checked before SDK dispatch.
- MCP initialization, tool discovery, and each tool call conform to the selected SDK's Streamable HTTP/JSON-RPC contract.
- Tool results preserve existing change parse errors as structured data and never expose project paths outside the tracked list.

### Manual Testing Steps:

1. Generate a local token, set `MCP_AUTH_TOKEN`, and launch Uvicorn on `127.0.0.1`.
2. Confirm missing and incorrect bearer credentials receive 401 responses.
3. Configure VS Code / GitHub Copilot and discover the three MCP tools.
4. Call status, recent-work, and next-action tools for representative tracked project states, including a malformed change and multiple active changes.
5. Rotate the secret, restart the process, and confirm old credentials no longer work.

## Performance Considerations

The first release reads local project metadata synchronously and is intended for a single desktop agent. It should avoid repeated parsing within one tool invocation by reusing shared service results, but it does not need caching, background indexing, or concurrency controls while the tool set remains read-only and local.

## Migration Notes

No stored-data migration is required. Existing tracked-project JSON and context files remain the source of truth. Adding the MCP dependency updates the project lock state through the repository's existing `python -m uv` workflow; users opt in by supplying `MCP_AUTH_TOKEN` and configuring their local MCP client.

## References

- Research: [context/changes/app-as-mcp/research.md](context/changes/app-as-mcp/research.md)
- Current application host: [app/main.py](app/main.py#L1-L7)
- Existing project API aggregate: [app/api.py](app/api.py#L28-L50)
- Change parsing and error preservation: [app/changes.py](app/changes.py#L22-L75)
- Phase progress behavior: [app/plan_progress.py](app/plan_progress.py#L42-L67)
- Roadmap table parser: [app/roadmap_correlation.py](app/roadmap_correlation.py#L16-L42)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Shared Read Models and Workflow Decisions

#### Automated

- [x] 1.1 New project-status service tests prove REST and service output use the same parsed aggregate — e41cfeb
- [x] 1.2 Roadmap parser tests cover prerequisites, status, ordering, absent tables, and malformed rows — e41cfeb
- [x] 1.3 Recent-work tests cover ordering, invalid dates, limits, and tracked-project-only scope — e41cfeb
- [x] 1.4 Workflow tests cover every recommendation rule, eligible prerequisites, multiple-active-change ambiguity, and malformed-state blocking — e41cfeb

#### Manual

- [x] 1.5 Inspect a fixture project with malformed `change.md` data and confirm valid records remain visible while the malformed record retains an explicit diagnostic
- [x] 1.6 Inspect a project with multiple active changes and confirm the service returns candidates without selecting a command

### Phase 2: Authenticated MCP Transport

#### Automated

- [ ] 2.1 Dependency resolution and application import succeed
- [ ] 2.2 MCP tests reject missing, malformed, and invalid Bearer tokens before tool dispatch
- [ ] 2.3 MCP protocol tests exercise initialization, `tools/list`, and each `tools/call` contract with a configured token
- [ ] 2.4 The full test suite passes

#### Manual

- [ ] 2.5 Start the server with a generated token on `127.0.0.1` and confirm an unauthenticated HTTP request to `/mcp` returns 401 without protocol output
- [ ] 2.6 Use VS Code / GitHub Copilot's configured MCP client to discover all three tools and invoke them against a tracked fixture or local project

### Phase 3: VS Code Setup and Operational Documentation

#### Automated

- [ ] 3.1 README commands use the repository-standard `python -m uv` invocation
- [ ] 3.2 The full test suite still passes after documentation and final integration work

#### Manual

- [ ] 3.3 Follow the README in a fresh PowerShell session to generate a token, launch the loopback-bound app, and configure VS Code / GitHub Copilot without placing the secret in version control
- [ ] 3.4 Discover and call each documented tool in VS Code / GitHub Copilot, then rotate the token and confirm that restarting the server is required before the new token works
