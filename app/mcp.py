import hmac
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool

from app.project_status import get_project_statuses
from app.recent_work import get_recent_work
from app.workflow_recommendations import get_next_10x_action


def _require_authentication(request: Request, expected_token: str) -> None:
    authorization = request.headers.get("Authorization", "")
    scheme, _, supplied_token = authorization.partition(" ")
    if scheme != "Bearer" or not supplied_token or not hmac.compare_digest(
        supplied_token, expected_token
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _to_text_content(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=data.model_dump_json())]


def create_mcp_server() -> Server:
    server = Server("10xDevTracker")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_project_status",
                description="Return the parsed status for persisted tracked projects.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_recent_work",
                description="Return recently updated change records from persisted tracked projects.",
                inputSchema={
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
                },
            ),
            Tool(
                name="get_next_10x_action",
                description="Recommend the next safe 10x workflow action for persisted tracked projects.",
                inputSchema={
                    "type": "object",
                    "properties": {"project_path": {"type": "string"}},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "get_project_status":
            return _to_text_content(get_project_statuses())
        if name == "get_recent_work":
            return _to_text_content(get_recent_work(arguments.get("limit", 10)))
        if name == "get_next_10x_action":
            return _to_text_content(get_next_10x_action(arguments.get("project_path")))
        raise ValueError(f"Unknown tool: {name}")

    return server


def add_mcp_transport(app: FastAPI) -> None:
    token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN must be set before starting the application")

    session_manager = StreamableHTTPSessionManager(
        create_mcp_server(), json_response=True, stateless=True
    )
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        async with original_lifespan(application):
            async with session_manager.run():
                yield

    app.router.lifespan_context = lifespan

    @app.post("/mcp")
    async def handle_mcp(request: Request) -> None:
        _require_authentication(request, token)
        await session_manager.handle_request(request.scope, request.receive, request._send)