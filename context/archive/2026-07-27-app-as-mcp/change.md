---
change_id: app-as-mcp
title: App as mcp
status: archived
created: 2026-07-27
updated: 2026-07-30
archived_at: 2026-07-30T14:36:12Z
---

## Notes

<!-- Free-form notes for this change: links, ad-hoc context, decisions that don't belong in research/frame/plan. -->

## Decisions

- Use the official Python MCP SDK for MCP protocol and transport handling.
- Keep FastAPI as the host for the existing web app, REST API, and MCP integration boundary.
- Do not hand-roll the MCP JSON-RPC protocol or use FastMCP.
