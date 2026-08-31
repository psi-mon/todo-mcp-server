"""Todo MCP server.

Task 1: `hello_world` for a connection check.
Task 2: `create_todo` persists a todo to ~/todos/todos.json.
Task 3: Read todos (tools + resources).
"""

from typing_extensions import type_repr
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError, ToolError
# ==============================================================================
# TASK 3 - LEARNING STEP: Imports for Resources & Error Handling
# ==============================================================================
# For Task 3, you will need the following additional imports:
#
# 1. From `mcp.server.mcpserver.exceptions`:
#    - `ResourceError`: Anticipated resource read failure (returns -32603)
#    - `ResourceNotFoundError`: Anticipated resource not found (returns -32602)
#
#    Example:
#    from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError, ToolError
#
# 2. From `todo_mcp.models`:
#    - `TodoListItem`: TypedDict containing only `name`, `status`, and `flag`
#
#    Example:
#    from todo_mcp.models import Todo, TodoListItem
#
# 3. From `todo_mcp.storage`:
#    - `TodoNotFoundError`: Specific error when a todo name isn't found
#    - `get_all_mcp_resources`: Helper function to generate MCPResource objects
#    - `TODOS_URI`, `TODO_TEMPLATE_URI`: Standardized URI constants
#
#    Example:
#    from todo_mcp.storage import (
#        TodoNotFoundError,
#        TodoStorageError,
#        get_all_mcp_resources,
#        store,
#    )
# ==============================================================================

from todo_mcp.models import Todo, TodoListItem
from todo_mcp.storage import TodoNotFoundError, TodoStorageError, get_all_combined_mcp_resources, get_all_mcp_resources, store

mcp = MCPServer(
    "todo-mcp",
    version="0.1.0",
    instructions=(
        "A local todo MCP server. Use create_todo to add a todo, "
        "list_todos to view summary items, get_todo to fetch full details, "
        "and resources under todo:// to inspect todo records directly."
    ),
)


@mcp.tool()
def create_todo(name: str, description: str | None = None) -> Todo:
    """Create a todo and save it to ~/todos/todos.json.

    Only name is required. Description is optional. Status is always "todo"
    and flag is always false. Names are unique (case-sensitive).
    """
    try:
        return store.create(name, description)
    except TodoStorageError as exc:
        raise ToolError(str(exc)) from exc


# ==============================================================================
# TASK 3: READ TODOS (TOOLS + RESOURCES)
# ==============================================================================


@mcp.tool()
def list_todos() -> list[TodoListItem]:
    try:
        return store.list_summary()
    except TodoStorageError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_todo(name: str) -> Todo:
    try:
        return store.get(name)
    except TodoNotFoundError as exc:
        raise ResourceNotFoundError(str(exc)) from exc
    except TodoStorageError as exc:
        raise ResourceError(str(exc)) from exc


@mcp.resource("todo://todos", mime_type="application/json")
def get_todos_resource() -> list[Todo]:
    try:
        return store.load()
    except TodoStorageError as exc:
        raise ResourceError(str(exc)) from exc

@mcp.resource("todo://todo/{name}", mime_type="application/json")
def get_todo_resource(name: str) -> Todo:
    try:
        return store.get(name)
    except TodoNotFoundError as exc:
        raise ResourceNotFoundError(str(exc)) from exc
    except TodoStorageError as exc:
        raise ResourceError(str(exc)) from exc


# --- 3. DYNAMIC RESOURCE LISTING (Cursor `@` Mention Picker) ------------------
#
# By default, `@mcp.resource("todo://todo/{name}")` registers a URI template.
# To let clients like Cursor list all existing concrete todo URIs when typing `@`,
# you can customize `mcp.list_resources` using the helper `get_all_mcp_resources`:
async def custom_list_resources():
    try:
        return get_all_mcp_resources(store)
    except TodoStorageError:
        return []

mcp.list_resources = custom_list_resources  # type: ignore[method-assign]


# ==============================================================================
# TASK 4: "DONE" FUNCTIONALITY FOR TODOS
# ==============================================================================
#
# Goal: Allow users to list all done todos and mark an active todo as done.
#
# --- 1. TOOL: get_done_todos --------------------------------------------------


@mcp.tool()
def get_done_todos() -> list[Todo]:
    try:
        return store.get_done_todos()
    except TodoStorageError as exc:
        raise ToolError(str(exc)) from exc

# --- 2. TOOL: mark_done -------------------------------------------------------
#

@mcp.tool()
def mark_done(name: str) -> Todo:
    try:
        return store.mark_done(name)
    except (TodoNotFoundError, TodoStorageError) as exc:
        raise ToolError(str(exc)) from exc

# ==============================================================================
# TASK 5: "FLAG" FUNCTIONALITY FOR TODOS (TOOLS + RESOURCES)
# ==============================================================================
#
# Goal: Allow users to flag a todo, list flagged todos, and expose flagged todos
# as MCP resources under the `flaggedTodo://` URI scheme.
#
# --- 1. TOOLS (For Agent Invocation) -------------------------------------------

@mcp.tool()
def flag_todo(name: str) -> Todo:
    try:
        return store.flag_todo(name)
    except (TodoNotFoundError, TodoStorageError) as exc:
        raise ToolError(str(exc)) from exc

@mcp.tool()
def list_flagged_todos() -> list[Todo]:
    try:
        return store.list_flagged_todos()
    except TodoStorageError as exc:
        raise ToolError(str(exc)) from exc

# --- 2. RESOURCES (For User `@` Mention & Direct Attachment) ------------------

@mcp.resource("flaggedTodo://todos", mime_type="application/json")
def get_flagged_todos_resource() -> list[Todo]:
    try:
        return store.list_flagged_todos()
    except TodoStorageError as exc:
        raise ResourceError(str(exc)) from exc

@mcp.resource("flaggedTodo://todo/{name}", mime_type="application/json")
def get_flagged_todo_resource(name: str) -> Todo:
    try:
        return store.get_flagged_todo(name)
    except TodoNotFoundError as exc:
        raise ResourceNotFoundError(str(exc)) from exc
    except TodoStorageError as exc:
        raise ResourceError(str(exc)) from exc

# --- 3. DYNAMIC RESOURCE LISTING UPDATE ---------------------------------------
#

async def custom_list_resources():
    try:
        return get_all_combined_mcp_resources(store)
    except TodoStorageError:
        return []

mcp.list_resources = custom_list_resources  # type: ignore[method-assign]

# ==============================================================================


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
