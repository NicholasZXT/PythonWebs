"""
演示 MCP 客户端使用
"""
from typing import TYPE_CHECKING
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.sse import sse_client
from mcp.client.websocket import websocket_client
from mcp.client.auth import OAuthContext, OAuthClientProvider, OAuthToken


def main():
    ...


if __name__ == '__main__':
    main()
