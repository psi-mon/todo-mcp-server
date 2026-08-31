# Todo MCP Server

A small local [MCP](https://modelcontextprotocol.io) server for creating and managing todos. This is a learning project.

Todos live in `~/todos/todos.json` (created automatically on first `create_todo`). The server still exposes `hello_world` so you can confirm the connection.

## Tech stack

- Python 3.13 (managed by `uv`)
- [`uv`](https://docs.astral.sh/uv/) for the project, venv, and dependencies
- Official MCP Python SDK (`mcp`), which includes the `MCPServer` helper and the `mcp` CLI
- **stdio** transport: the client starts this process and talks JSON-RPC over stdin/stdout

## How the setup fits together

1. **`uv`** creates `.venv`, installs `mcp`, and runs the `todo-mcp` console script from this project's environment. Clients should launch the server with `uv run` (or `uv --directory … run`) so they always use that environment — not system Python.
2. **The SDK** turns decorated Python functions into MCP tools. The function name is the tool name, the docstring is the description, and type hints become the JSON Schema the Inspector shows.
3. **stdio** means this process does not open a port. The host (Inspector or Cursor) spawns `uv run todo-mcp` and exchanges MCP messages on stdin/stdout. Do not `print()` to stdout; that corrupts the protocol. Logging can go to stderr.
4. **The Inspector** is a standalone MCP client with a UI. It starts your server as a subprocess, lists tools, and lets you call them. That is the acceptance check for this task.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js **≥ 22.19** (only needed for the Inspector via `npx`). Inspector 2 imports `styleText` from `node:util`, which does not exist on Node 18.

If you use **nvm**, this repo has an `.nvmrc` pinning 22. `mcp dev` shells out to `npx`, so it uses whatever `node` is on your PATH — not the Python venv:

```bash
nvm install   # reads .nvmrc
nvm use
node -v       # should print v22.x or newer
```

From this directory:

```bash
uv sync
```

That installs dependencies from `uv.lock` into `.venv`.

## Run the server

On its own the process waits for MCP messages on stdin (it looks hung; that is expected):

```bash
uv run todo-mcp
```

Stop it with Ctrl+C. Prefer the Inspector below instead of running it by hand.

## Inspect with the MCP Inspector

`uv run mcp dev` is the SDK helper, but it launches **Inspector v2** via `npx` using whatever `node` is on your PATH. That currently fails here in two ways:

| What you see | Cause |
|---|---|
| `node:util` / `styleText` | nvm default is Node 18; Inspector 2 needs ≥ 22.19 |
| `Cannot find native binding` | Inspector v2's keyring optional native addon; `npx` often skips it ([inspector#1852](https://github.com/modelcontextprotocol/inspector/issues/1852)) |
| `Failed to spawn: dev` | There is no `dev` binary. The SDK command is `uv run mcp dev …` |

Use the project launcher instead (picks Node ≥ 22.19 and pins Inspector v1):

```bash
uv run todo-mcp-inspect
```

You do **not** need `nvm use` first for this command. Open the URL it prints (usually `http://localhost:6274`).

The leftover warning `VIRTUAL_ENV=…/cli_project/.venv does not match` is from another project's venv still being active. It is ignored; `deactivate` in that terminal if you want it gone.

Equivalent, by hand, with a new enough Node:

```bash
npx --yes @modelcontextprotocol/inspector@v1-latest -- uv --directory /ABSOLUTE/PATH/TO/todo-mcp run todo-mcp
```

### Confirm `hello_world`

1. Open the URL the Inspector prints (usually `http://localhost:6274`).
2. Connect if it does not connect automatically.
3. Open the **Tools** tab. You should see `hello_world`.
4. Run it with no arguments (default name `World`) or pass `"name": "Inspector"`.
5. The result should look like: `Hello, Inspector! The todo MCP server is running.`

### Test `create_todo`

After connecting, you should also see **`create_todo`** in Tools. The input schema has `name` (required string) and `description` (optional string). `status` and `flag` are **not** inputs; the server always writes `"todo"` and `false`.

Use a throwaway name so you can repeat the duplicate-name case.

1. **Happy path (name only).** Call `create_todo` with `"name": "buy milk"`. The result should be the full todo object, for example:

   ```json
   {
     "name": "buy milk",
     "status": "todo",
     "flag": false
   }
   ```

   `~/todos/todos.json` should now exist as a JSON array containing that object.

2. **Optional description.** Call `create_todo` with `"name": "write report"` and `"description": "draft the intro"`. The result should include `"description": "draft the intro"` as well as `status` and `flag`.

3. **Duplicate name.** Call `create_todo` again with `"name": "buy milk"`. The tool should fail with a clear error (`A todo named 'buy milk' already exists.`) and `todos.json` should still have only one item with that name.

Leading/trailing spaces on `name` are trimmed. A blank name is rejected. If `todos.json` exists but is invalid JSON (or not an array), the tool errors instead of overwriting the file.

Close the Inspector with **Ctrl+C** in the terminal that started it so ports 6274/6277 are freed before you start it again.

### Test `list_todos` and `get_todo` (Tools)

1. **List todos (`list_todos`).** Open the Tools tab and run `list_todos` with no parameters. It returns a concise array of todos with `name`, `status`, and `flag` (descriptions omitted).
2. **Get specific todo (`get_todo`).** Call `get_todo` with `"name": "buy milk"`. It returns the full todo object (including `description` if set).
3. **Not found case.** Call `get_todo` with a non-existent name like `"does not exist"`. The tool fails with a clear not-found error.

### Test Resources (`todo://todos` and `todo://todo/{name}`)

1. **Collection resource (`todo://todos`).** Open the **Resources** tab in the Inspector. Select `todo://todos` and click Read. It displays the full JSON array of all todos (`mimeType: application/json`).
2. **Individual resource (`todo://todo/{name}`).** Read `todo://todo/buy%20milk` (or `todo://todo/buy milk`). It returns the JSON object for that specific todo. If the todo does not exist, the server returns an invalid-params error (`-32602`).

### Test Task 4: "Done" Functionality (`get_done_todos` and `mark_done`)

1. **Mark a todo as done (`mark_done`).** Call `mark_done` with `"name": "buy milk"`. The item is removed from `~/todos/todos.json` and saved in `~/todos/donedos.json` with status `"done"`.
2. **List done todos (`get_done_todos`).** Run `get_done_todos` to view all completed todos from `~/todos/donedos.json`.
3. **Verify active list (`list_todos`).** Run `list_todos` to verify that `"buy milk"` is no longer in the active list.
4. **Not found case.** Call `mark_done` with a todo name that is not in `todos.json` (e.g. `"nonexistent"`). It should raise a clear not-found error.

## How `create_todo` is implemented (MCP tools)

This is the Task 2 walkthrough, focused on MCP rather than the JSON file format.

1. **Register a tool with `@mcp.tool()`.** In `src/todo_mcp/server.py`, `create_todo` is a normal Python function. The decorator publishes it on the server. Clients discover it via `tools/list`; the Inspector Tools tab is that list.

2. **Name.** The Python function name **is** the MCP tool name (`create_todo`). That is what agents and the Inspector call.

3. **Description.** The function docstring is the tool description sent to the model. It should say what the tool does, which arguments matter, and the uniqueness rule.

4. **Input schema from type hints.** MCP does not use a hand-written JSON Schema here. `name: str` becomes a required string. `description: str | None = None` becomes an optional string. There are no `status` or `flag` parameters, so callers cannot set them on create.

5. **Result.** The function returns a `Todo` dict (name, status, flag, and description when present). The SDK puts that in the tool result (`structured_content` plus a JSON text block). Returning the object — not only `"ok"` — lets the model see what was stored.

6. **Anticipated errors.** Duplicate names, empty names, and a corrupt `todos.json` raise `ToolError`. The client gets `is_error=true` and the message. Other exceptions are treated as crashes and hide the details.

File I/O lives in `src/todo_mcp/storage.py` (`TodoStore`) so the tool stays a thin MCP wrapper: validate/raise `ToolError`, return the todo. Persistence is `~/todos/todos.json` (a JSON array). The folder and file are created on first successful create.

## How Task 3 is implemented (MCP Resources vs Tools)

### Tools vs Resources

| Feature | MCP Tools | MCP Resources |
|---|---|---|
| **Target Audience** | Invoked autonomously by the LLM agent | Attached or selected by the user (via `@` in Cursor / Inspector) |
| **Addressing** | Called by function name (e.g. `list_todos`, `get_todo`) | Identified by standard URIs (e.g. `todo://todos`, `todo://todo/{name}`) |
| **Parameters** | Passed as typed arguments | Extracted from RFC 6570 URI templates |
| **MIME Type** | JSON structured content + text | Declared content type (`application/json`, `text/plain`, etc.) |
| **Error Signaling** | `ToolError` (returns `is_error=True`) | `ResourceNotFoundError` (`-32602`), `ResourceError` (`-32603`) |

### Key Concepts in Task 3

1. **Resource Templates (`@mcp.resource("todo://todo/{name}")`):**
   The `{name}` parameter in the URI template automatically maps to the function argument `name: str`. The SDK parses and validates URI template parameters before invoking your handler.
2. **Collection Resource (`@mcp.resource("todo://todos")`):**
   A static URI without variables. Reading this resource returns the entire array of todos.
3. **MIME Types:**
   Setting `mime_type="application/json"` explicitly informs clients that the returned payload is JSON data rather than raw plain text.
4. **Dynamic Resource Listing:**
   When the user types `@` in an MCP host like Cursor, the client calls `resources/list`. Overriding `mcp.list_resources` dynamically returns individual `MCPResource` records for every item currently in `~/todos/todos.json`.

## Use it in Cursor

Add a stdio server entry to Cursor's MCP config. Project-level file: `.cursor/mcp.json`. User-level: Cursor Settings → MCP.

```json
{
  "mcpServers": {
    "todo-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/todo-mcp",
        "run",
        "todo-mcp"
      ]
    }
  }
}
```

Use an absolute path for `--directory`. If Cursor cannot find `uv`, put the full path from `which uv` in `"command"` (often `/opt/homebrew/bin/uv` on Apple Silicon).

After saving, reload MCP (or restart Cursor). `hello_world` and `create_todo` should appear in the tool list. You can also ask the agent to call them.

## Use it in Claude Code

Claude Code is a separate CLI from this repo. Install the [Claude Code CLI](https://code.claude.com/docs/en/quickstart) so the `claude` command is on your PATH, then register this server as a **stdio** MCP server.

From this project's root (`pwd` must be this repo):

```bash
uv sync
claude mcp add --transport stdio todo-mcp -- "$(which uv)" --directory "$(pwd)" run todo-mcp
```

The `--` is required: everything after it is the launch command Claude Code runs, not flags for `claude mcp add`. `--directory` must be an **absolute** path (`$(pwd)` when you are in this folder). `"$(which uv)"` avoids Claude Code failing to find `uv` on PATH (common with Homebrew).

You should see a line like `Added stdio MCP server todo-mcp …`. Check the connection:

```bash
claude mcp list
```

`todo-mcp` should show as connected. Then start a session (`claude`) and ask it to call `hello_world` or `create_todo`. You can also open `/mcp` inside the session.

**Scopes** (`-s` / `--scope`): `local` (default, this project, only you), `user` (all your projects), `project` (writes `.mcp.json` in the repo for the team). To remove it:

```bash
claude mcp remove todo-mcp
```

If it fails to connect, run the launch command yourself (`uv --directory "$(pwd)" run todo-mcp`). If that looks hung, stdio is working; if it errors, fix that before adding it again.

## Use it in Antigravity (`agy`)

Antigravity uses `mcp_config.json` to configure MCP servers. You can register `todo-mcp` globally across all projects or locally within a project workspace/plugin.

### Global Configuration

Add the server definition to your global MCP configuration at `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "todo-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/todo-mcp",
        "run",
        "todo-mcp"
      ]
    }
  }
}
```

> **Note:** Replace `/ABSOLUTE/PATH/TO/todo-mcp` with the absolute path to this repository (`pwd`). If `agy` cannot find `uv` on your PATH, specify the full path from `which uv` (e.g., `/opt/homebrew/bin/uv` or `~/.cargo/bin/uv`).

### Workspace / Plugin Configuration

To share the configuration with your project/team as an Antigravity plugin, place the config in `.agents/plugins/<plugin_name>/mcp_config.json`.

### Verification

1. Start or restart `agy` (or your Antigravity IDE / session).
2. The agent automatically discovers `hello_world` and `create_todo` on startup.
3. Prompt the agent to test the tools (e.g., *"Run hello_world from todo-mcp"* or *"Create a todo to buy milk"*).


