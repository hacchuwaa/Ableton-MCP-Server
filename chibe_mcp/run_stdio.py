"""Chibe MCP - Run with Stdio transport (for Claude Desktop / AI clients)."""
from chibe_mcp.server import mcp


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
