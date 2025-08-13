"""
演示 MCP 服务端使用
"""
from typing import TYPE_CHECKING
from mcp.server import FastMCP, Server
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
# from mcp.server.auth


mcp = FastMCP("Demo")


def main():
    ...


if __name__ == '__main__':
    main()
