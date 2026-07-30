---
change_id: app-as-mcp
title: App as mcp
status: implemented
created: 2026-07-27
updated: 2026-07-30
archived_at: null
---

## Notes

<!-- Free-form notes for this change: links, ad-hoc context, decisions that don't belong in research/frame/plan. -->

## Decisions

- Use the official Python MCP SDK for MCP protocol and transport handling.
- Keep FastAPI as the host for the existing web app, REST API, and MCP integration boundary.
- Do not hand-roll the MCP JSON-RPC protocol or use FastMCP.
