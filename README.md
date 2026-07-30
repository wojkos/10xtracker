# 10xDevTracker

## Running the app

Start the browser app with Uvicorn:

```powershell
python -m uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open http://127.0.0.1:8000/ in a browser.

## MCP server

10xDevTracker also provides a local, read-only MCP server for VS Code and GitHub
Copilot at `http://127.0.0.1:8000/mcp`. It only reads projects persisted in
10xDevTracker's tracked-project list.

Generate a token in PowerShell, then set it only in the environment of the
process that starts the server:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
$env:MCP_AUTH_TOKEN = "<generated-token>"
python -m uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Do not add the token to tracked project files or commit it. The server fails
closed when `MCP_AUTH_TOKEN` is unset. To rotate the token, set a new value and
restart the server; the prior token stops working after the restart.

Configure VS Code / GitHub Copilot with an authenticated Streamable HTTP MCP
server. Keep the secret in supported local configuration, rather than in a
repository file:

```json
{
	"servers": {
		"10xDevTracker": {
			"type": "http",
			"url": "http://127.0.0.1:8000/mcp",
			"headers": {
				"Authorization": "Bearer ${input:10xDevTrackerToken}"
			}
		}
	}
}
```

After saving the local configuration and entering the generated token, discover
and call these read-only tools:

- `get_project_status` returns the parsed aggregate for tracked projects.
- `get_recent_work` returns recently updated change records; its timestamp is
	record-update data, not an audit history.
- `get_next_10x_action` returns a conservative workflow recommendation for
	tracked projects, or candidates and a blocking question when it cannot safely
	choose.
