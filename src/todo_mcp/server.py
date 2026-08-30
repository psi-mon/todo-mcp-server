"""Todo MCP server.

Task 1: `hello_world` for a connection check.
Task 2: `create_todo` persists a todo to ~/todos/todos.json.
"""

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from todo_mcp.models import Todo
from todo_mcp.storage import TodoStorageError, store

mcp = MCPServer(
    "todo-mcp",
    version="0.1.0",
    instructions=(
        "A local todo MCP server. Use hello_world to confirm the connection, "
        "and create_todo to add a todo (name required, description optional)."
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


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
