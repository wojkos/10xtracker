import hmac
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from pydantic import TypeAdapter
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Match
from starlette.types import Receive, Scope, Send

from app.project_status import get_project_statuses
from app.recent_work import get_recent_work
from app.workflow_recommendations import get_next_10x_action

ENV_FILE = Path(__file__).parent.parent / ".env"


def _get_mcp_token() -> str:
    return os.environ.get("MCP_AUTH_TOKEN") or dotenv_values(ENV_FILE).get(
        "MCP_AUTH_TOKEN", ""
    )


def _require_authentication(request: Request, expected_token: str) -> None:
    authorization = request.headers.get("Authorization", "")
    scheme, _, supplied_token = authorization.partition(" ")
    if scheme != "Bearer" or not supplied_token or not hmac.compare_digest(
        supplied_token, expected_token
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _to_text_content(data: Any) -> list[TextContent]:
    return [
        TextContent(
            type="text",
            text=TypeAdapter(Any).dump_json(data).decode("utf-8"),
        )
    ]


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
            return _to_text_content(
                {
                    "timestamp_interpretation": "record-update data",
                    "items": get_recent_work(arguments.get("limit", 10)),
                }
            )
        if name == "get_next_10x_action":
            return _to_text_content(get_next_10x_action(arguments.get("project_path")))
        raise ValueError(f"Unknown tool: {name}")

    return server


class MCPRoute(BaseRoute):
    def __init__(self, session_manager: StreamableHTTPSessionManager, token: str) -> None:
        self.session_manager = session_manager
        self.token = token

    def matches(self, scope: Scope) -> tuple[Match, dict[str, Any]]:
        if scope["type"] == "http" and scope["path"] == "/mcp":
            return Match.FULL, {}
        return Match.NONE, {}

    def url_path_for(self, name: str, /, **path_params: Any) -> Any:
        raise RuntimeError("The MCP route has no named URL")

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive)
        try:
            _require_authentication(request, self.token)
        except HTTPException:
            await JSONResponse({"detail": "Unauthorized"}, status_code=401)(
                scope, receive, send
            )
            return
        await self.session_manager.handle_request(scope, receive, send)


def add_mcp_transport(app: FastAPI) -> None:
    token = _get_mcp_token()
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

    app.router.routes.append(MCPRoute(session_manager, token))