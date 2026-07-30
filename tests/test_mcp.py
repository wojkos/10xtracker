import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import mcp, projects
from app.mcp import add_mcp_transport


@pytest.fixture(autouse=True)
def _isolated_data_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(projects, "DATA_FILE", tmp_path / "data" / "tracked_projects.json")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("MCP_AUTH_TOKEN", "test-token")
    app = FastAPI()
    add_mcp_transport(app)
    return TestClient(app)


def _request(method: str, params: dict | None = None) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token", "Accept": "application/json"}


def test_missing_mcp_token_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(mcp, "ENV_FILE", Path("missing.env"))
    with pytest.raises(RuntimeError, match="MCP_AUTH_TOKEN"):
        add_mcp_transport(FastAPI())


def test_mcp_token_loads_from_root_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("MCP_AUTH_TOKEN=dotenv-token\n", encoding="utf-8")
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(mcp, "ENV_FILE", dotenv_file)

    app = FastAPI()
    add_mcp_transport(app)

    assert app.router.routes[-1].token == "dotenv-token"


@pytest.mark.parametrize("authorization", [None, "Basic test-token", "Bearer wrong-token"])
def test_mcp_rejects_invalid_credentials_before_dispatch(
    client: TestClient, authorization: str | None
) -> None:
    headers = {"Accept": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization

    response = client.post("/mcp", json=_request("tools/list"), headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_mcp_lists_and_calls_read_only_tools(client: TestClient) -> None:
    with client:
        initialize = client.post(
            "/mcp",
            json=_request(
                "initialize",
                {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
            ),
            headers=_headers(),
        )
        assert initialize.status_code == 200

        tools = client.post("/mcp", json=_request("tools/list"), headers=_headers())
        assert tools.status_code == 200
        assert {tool["name"] for tool in tools.json()["result"]["tools"]} == {
            "get_project_status",
            "get_recent_work",
            "get_next_10x_action",
        }

        for tool_name in ("get_project_status", "get_recent_work", "get_next_10x_action"):
            response = client.post(
                "/mcp",
                json=_request("tools/call", {"name": tool_name, "arguments": {}}),
                headers=_headers(),
            )
            assert response.status_code == 200
            content = response.json()["result"]["content"][0]
            assert content["type"] == "text"
            tool_result = json.loads(content["text"])
            if tool_name == "get_recent_work":
                assert tool_result["timestamp_interpretation"] == "record-update data"