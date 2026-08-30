"""Todo MCP server.

Task 1 exposes a `hello_world` tool so the stdio server can be verified in the
MCP Inspector. Todo tools land in later tasks.
"""

from mcp.server import MCPServer

mcp = MCPServer(
    "todo-mcp",
    version="0.1.0",
    instructions="A local todo MCP server. Call hello_world to confirm the connection.",
)


@mcp.tool()
def hello_world(name: str = "World") -> str:
    """Return a short greeting. Use this to confirm the MCP server is connected."""
    return f"Hello, {name}! The todo MCP server is running."


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
