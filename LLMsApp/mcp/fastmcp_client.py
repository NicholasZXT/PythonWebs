"""
练习 FastMCP 客户端使用
"""
import os
from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel, Field
import asyncio
from fastmcp import settings, Client, FastMCP

print(f"current working directory: {os.getcwd()}")
# FastMCP 提供了 3 种方式来初始化客户端：
#   1. Local Python script —— 本地Python脚本启动，对应于 stdio 模式
client = Client(transport="fastmcp_server.py")
#   2. HTTP server
# client = Client(transport="https://example.com/mcp")
#   3. In-memory server (ideal for testing) —— 一般用于测试
# from fastmcp_server import fastmcp
# client = Client(transport=fastmcp)


async def fastmcp_client_basic_usage():
    async with client:
        # Basic server interaction
        ping_res = await client.ping()
        print(f"mcp server ping res: {ping_res}")
        print("--------------------------------")

        # List available operations
        tools = await client.list_tools()
        # print(tools)
        for tool in tools:
            # print(f"tool.__class__: {tool.__class__}")   # <class 'mcp.types.Tool'>
            print(f"tool.name: {tool.name}, tool.description: {tool.description}")
        print("--------------------------------")

        resources = await client.list_resources()
        # print(resources)
        for resource in resources:
            # print(f"resource.__class__: {resource.__class__}")  # <class 'mcp.types.Resource'>
            print(f"resource.uri: {resource.uri}, resource.description: {resource.description}")
        print("--------------------------------")

        resource_templates = await client.list_resource_templates()
        # print(resource_templates)
        for template in resource_templates:
            # print(f"template.__class__: {template.__class__}")  # <class 'mcp.types.ResourceTemplate'>
            print(f"template.uriTemplate: {template.uriTemplate}, template.description: {template.description}")
        print("--------------------------------")

        prompts = await client.list_prompts()
        # print(prompts)
        for prompt in prompts:
            # print(f"prompt.__class__: {prompt.__class__}")  # <class 'mcp.types.Prompt'>
            print(f"prompt.name: {prompt.name}, prompt.description: {prompt.description}")
        print("--------------------------------")

        # Execute operations
        result = await client.call_tool("get_weather", arguments={"city": "杭州"})
        # print(f"result.__class__: {result.__class__}")  # <class 'fastmcp.client.client.CallToolResult'>
        print(result)
        print(result.content)
        print(result.structured_content)


def main():
    asyncio.run(fastmcp_client_basic_usage())


if __name__ == '__main__':
    main()
