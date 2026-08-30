# Todo MCP Server — Tasks

Learning project: a small local MCP server for creating and reading todos.

Update, delete, and mark-done are **out of scope** here and will be added later. `status` and `flag` still belong in the schema so later tasks can change them.

## Shared conventions

These apply to every task. Do not contradict them in later work without updating this section.

- **Stack:** Python, `uv`, official MCP Python SDK (`mcp`)
- **Transport:** stdio
- **Acceptance client:** MCP Inspector (`npx @modelcontextprotocol/inspector`). Also document a Cursor `mcp.json` snippet so the server can be used in the editor.
- **Storage:** single file `~/todos/todos.json`. Create the folder and file if they do not exist. Ignore any `donedos.json` / `~/todo/` layout until a later task.
- **JSON shape:** a JSON array of todo objects
- **Todo schema:**

  | Field | Type | Notes |
  |---|---|---|
  | `name` | string | Required, unique, case-sensitive. Trim whitespace. Reject empty names. |
  | `description` | string or omitted | Optional |
  | `status` | `"todo"` or `"done"` | Always `"todo"` on create |
  | `flag` | boolean | Generic boolean marker (e.g. important). Always `false` on create |

- **Names are unique.** Create fails if a todo with that name already exists. Task 3 looks up by exact name.
- **Invalid file:** if `todos.json` exists but is not valid JSON (or not an array), tools/resources return a clear error instead of overwriting silently.
- **Hello World:** keep the Task 1 demo tool until a later cleanup task says otherwise.

---

## Task 1: Project setup

**Goal:** Set up the project and dependencies so the MCP server can be started and inspected.

**Details:**

- Minimal Python package runnable with `uv`
- Server speaks MCP over **stdio**
- One demo **tool** named something like `hello_world` that returns a short greeting (so it is visible in the Inspector tool list)
- Document how to run the Inspector against this stdio server
- Document how to register the server in Cursor (`mcp.json`)
- Short explanation of the setup: `uv`, the SDK, stdio, and how the Inspector attaches

**Key deliverables:**

- Source and config enough to start the server
- Hello World tool visible in the Inspector
- Instructions: start Inspector, start server, confirm the tool
- Short write-up of the setup process

---

## Task 2: Create Todo tool

**Goal:** Add an MCP **tool** that creates a todo and persists it to `~/todos/todos.json`.

**Details:**

- Tool input: `name` (required), `description` (optional). Do not accept `status` or `flag` from the caller.
- On success: append the new todo with `status: "todo"` and `flag: false`. Create `~/todos/` and `todos.json` if needed (`[]` then one item).
- On duplicate name: fail with a clear error; do not create a second item.
- Return the full created todo object in the tool result (not only a success string).
- Do not implement update, delete, or mark-done.

**Key deliverables:**

- Readable, organized code for the create tool and file I/O
- Instructions for testing create in the Inspector (happy path, optional description, duplicate name)
- Step-by-step guide of the implementation, focused on MCP tool features (name, description, input schema, result)

---

## Task 3: Read todos (tools + resources)

**Goal:** Expose todos as MCP **resources** (so `@` mention works) and as **tools** (list + get by name).

**Details:**

**Tools**

- `list_todos`: return every todo. Include `name`, `status`, and `flag`. Descriptions may be omitted in the list to keep it short.
- `get_todo`: required `name`; return the full todo (name, description, flag, status). Exact, case-sensitive match. If missing, return a clear not-found error.
- List includes all statuses (`todo` and `done`). No filtering in this task.

**Resources (for `@` in Cursor)**

- URI scheme: `todo://`
- `list_resources` returns **one resource per todo**, e.g. `todo://todo/{name}`, so the user can `@` and pick a specific todo
- Also expose a list resource `todo://todos` whose contents are the full JSON array
- Reading `todo://todo/{name}` returns that todo as `application/json` (full object)
- Use a resource template `todo://todo/{name}` so clients can complete names

Both surfaces read the same `~/todos/todos.json`. Tools are for agents; resources are for `@` attach/select.

**Key deliverables:**

- List tool and get-by-name tool
- Resources so the user can `@` all todos and select one
- Step-by-step guide focused on MCP resources vs tools (URIs, `list_resources`, templates, mime type)
