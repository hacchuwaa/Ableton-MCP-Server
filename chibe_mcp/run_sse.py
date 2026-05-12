"""Chibe MCP - Run with SSE transport.

Connects to the Chibe Remote Script running inside Ableton Live.
Default: http://127.0.0.1:8501/sse
"""
from chibe_mcp.server import mcp


def main():
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
