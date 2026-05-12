"""Chibe MCP - Run with Streamable HTTP transport (default, recommended).

Connects to the Chibe Remote Script running inside Ableton Live.
Default: http://127.0.0.1:8000/mcp
"""
from chibe_mcp.server import mcp


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
