# App as MCP - Plan Brief

> Full plan: [context/changes/app-as-mcp/plan.md](context/changes/app-as-mcp/plan.md)
> Research: [context/changes/app-as-mcp/research.md](context/changes/app-as-mcp/research.md)

## What & Why

10xDevTracker will become a desktop-local, read-only MCP server for VS Code / GitHub Copilot. A chat agent will be able to inspect tracked-project status, see recently updated change records, and receive a safe next 10x workflow action without parsing local context files itself.

## Starting Point

The FastAPI application already aggregates persisted tracked projects through REST and reads change status, plan progress, and basic roadmap correlation from context files. It has no MCP endpoint, shared status service, workflow recommendation logic, roadmap prerequisite model, or authentication boundary for an agent client.

## Desired End State

With a manually generated `MCP_AUTH_TOKEN` and a loopback-bound Uvicorn server, VS Code / GitHub Copilot can discover three tools at `/mcp`: `get_project_status`, `get_recent_work`, and `get_next_10x_action`. Every tool remains read-only and scoped to the persisted tracked-project list; uncertain workflow state produces structured candidates or a blocking question rather than an invented command.

## Key Decisions Made

| Decision | Choice | Why | Source |
| --- | --- | --- | --- |
| Protocol implementation | Official Python MCP SDK under FastAPI | The SDK owns Streamable HTTP and JSON-RPC semantics while the existing host remains unchanged. | Research |
| Supported client | VS Code / GitHub Copilot first | It is the active development environment, making compatibility and setup testable. | Plan |
| Data scope | Persisted tracked projects only | Prevents an agent from broadening filesystem access with arbitrary paths. | Plan |
| Roadmap eligibility | Parse and enforce prerequisites | New-work recommendations must respect declared dependency order. | Plan |
| Ambiguous active work | Return candidates with no command | Project recency and roadmap order are not sufficient priority policy. | Plan |
| Authentication | Startup-captured environment bearer token | It fails closed without introducing secret persistence or reload behavior. | Plan |
| Error behavior | Structured partial data, no unsafe recommendation | A malformed file should remain visible without hiding healthy project records. | Plan |

## Scope

**In scope:**

- Shared read-only project status for REST and MCP.
- Recent-record ordering, roadmap prerequisite parsing, and conservative workflow recommendations.
- Authenticated Streamable HTTP MCP endpoint with three discoverable read-only tools.
- MCP protocol, service, and documentation tests plus VS Code / GitHub Copilot setup guidance.

**Out of scope:**

- MCP mutations, remote hosting, arbitrary-project reads, FastMCP, custom JSON-RPC, audit history, and dynamic token rotation.

## Architecture / Approach

FastAPI continues to host the web application and REST API. A shared status service, recent-work service, and workflow recommendation service read the existing files; the MCP adapter authenticates requests and delegates protocol lifecycle to the official SDK. The adapter never writes project/context data and never resolves a path outside `tracked_projects.json`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Shared Read Models and Workflow Decisions | Reusable status, ordered recent work, dependency-aware roadmap data, and conservative recommendations | Context-file format ambiguity could make a recommendation unsafe. |
| 2. Authenticated MCP Transport | SDK-backed `/mcp`, startup token auth, and three tool contracts | Streamable HTTP/client behavior must match VS Code / GitHub Copilot. |
| 3. VS Code Setup and Operational Documentation | Secure local launch and client configuration path | Configuration must not accidentally expose the secret or bind beyond loopback. |

**Prerequisites:** Python 3.13 environment, `python -m uv`, a manually generated local secret, and at least one persisted tracked project for meaningful tool results.
**Estimated effort:** ~2-3 sessions across 3 phases.

## Open Risks & Assumptions

- The official MCP SDK version selected during implementation must provide FastAPI-compatible Streamable HTTP integration verified with VS Code / GitHub Copilot.
- Roadmap recommendations depend on consistent status/prerequisite text in the `## At a glance` table; malformed or incomplete rows deliberately block automatic selection.
- Token rotation interrupts local MCP access until Uvicorn restarts.

## Success Criteria (Summary)

- Authenticated VS Code / GitHub Copilot can discover and call all three read-only tools at local `/mcp`.
- Status and recent-work results preserve existing parsed data and errors without expanding project scope.
- Next-action output chooses only a provably eligible workflow step and declines to choose when active work or artifacts are ambiguous.
