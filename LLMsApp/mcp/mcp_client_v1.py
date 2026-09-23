"""
演示 MCP 客户端使用
"""
import sys
import os
from typing import TYPE_CHECKING, Optional
from pydantic import BaseModel, Field, AnyUrl
from contextlib import AsyncExitStack
import asyncio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import types
from mcp.shared.context import RequestContext
from mcp.client.session import ClientSession
from mcp.client.session_group import ClientSessionGroup
from mcp.shared.metadata_utils import get_display_name
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.websocket import websocket_client
from mcp.client.auth import OAuthContext, OAuthClientProvider, OAuthToken
from logging_util import getLogger

# stdio 模式下的客户端可以正常使用 print 输出
# logger = getLogger(name='mcp_client', debug=True, write_file=True)


async def stdio_client_connect_usage():
    """
    演示 stdio 模式下 MCP 客户端 如何连接 服务端。
    sse_client, streamablehttp_client 也是这个流程，不过它们不需要 StdioServerParameters 类似的param封装
    """
    print(f"current working directory: {os.getcwd()}")
    # 1. 首先封装一个 StdioServerParameters 对象，里面存放的是启动 MCP 服务端的命令行参数，后续服务端会作为子进程被启动
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py", "--transport", "stdio"],
        env={"UV_INDEX": os.environ.get("UV_INDEX", "")},
        cwd=os.getcwd(),
    )

    # 2. 使用 StdioServerParameters 对象创建一个 stdio_client，结合 async with 上下文管理器，
    # 返回一对 (read, write)，它们是 anyio 的 MemoryObjectReceiveStream / MemoryObjectSendStream 对象，用于和MCP服务子进程进行双向通信
    async with stdio_client(server_params) as (read, write):
        print(f"read.__class__: {read.__class__}, write.__class__: {write.__class__}")

        # 3. 使用 ClientSession 封装 stdio_client 返回的 (read, write) 对象，并初始化连接
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            # <mcp.client.session.ClientSession>
            print(f"session: {session} initialized.")

            # ----- 查询 MCP服务端 提供的 tools, resources, prompts -----
            # List available tools
            tools_result: types.ListToolsResult = await session.list_tools()
            # print(f"tools_result.__class__: {tools_result.__class__}")   # <class 'mcp.types.ListToolsResult'>
            print(f"Available tools: {[t.name for t in tools_result.tools]}")
            for tool in tools_result.tools:
                # MCP SDK 提供了一个工具，用于获取工具元数据，它获取的是 @mcp.tool 的 title，@mcp.resource 的 name
                print(f"Tool: {get_display_name(tool)}")

            # List available resources
            # 这里只会列出静态URI，不会列出动态URI资源
            resources_result: types.ListResourcesResult = await session.list_resources()
            # print(f"resources_result.__class__: {resources_result.__class__}")  # <class 'mcp.types.ListResourcesResult'>
            # print(f"resource count: {len(resources_result.resources)}")
            print(f"Available resources: {[r.uri for r in resources_result.resources]}")
            for resource in resources_result.resources:
                print(f"Resource: {get_display_name(resource)}")

            # 下面这个方法才会列出动态URI资源
            resource_templates_result: types.ListResourceTemplatesResult = await session.list_resource_templates()
            print(f"Available resource_templates: {[r.uriTemplate for r in resource_templates_result.resourceTemplates]}")
            for resource_template in resource_templates_result.resourceTemplates:
                print(f"Resource template: {get_display_name(resource_template)}")

            # List available prompts
            prompts_result: types.ListPromptsResult = await session.list_prompts()
            # print(f"prompts_result.__class__: {prompts_result.__class__}")  # <class 'mcp.types.ListPromptsResult'>
            print(f"Available prompts: {[p.name for p in prompts_result.prompts]}")
            for prompt in prompts_result.prompts:
                print(f"Prompt: {get_display_name(prompt)}")

            # ----- 调用/获取 MCP服务端 提供的 tools, resources, prompts -----
            # Call a tool
            print("Calling tool...")
            result = await session.call_tool("get_weather", arguments={"city": "杭州"})
            result_unstructured = result.content[0]
            if isinstance(result_unstructured, types.TextContent):
                print(f"Tool result: {result_unstructured.text}")
            result_structured = result.structuredContent
            print(f"Structured tool result: {result_structured}")

            # Read a resource
            print("Reading resource...")
            resource_content = await session.read_resource(AnyUrl("greeting://World"))
            content_block = resource_content.contents[0]
            print(f"Resource content: {content_block.text}")

            # Get a prompt
            print("Reading prompt...")
            if prompts_result.prompts:
                prompt = await session.get_prompt("greet_user_prompt", arguments={"name": "Alice", "style": "friendly"})
                print(f"Prompt result: {prompt.messages[0].content}")


class MCPClient:
    """
    官方提供的一个 MCPClient 封装示例，个人略有修改。
    主要是使用 AsyncExitStack 来管理 (ReadStream, WriteStream) 和 ClientSession 的上下文。
    """
    def __init__(self, llm_client):
        # Initialize session and client objects
        self.stdio: Optional[MemoryObjectReceiveStream] = None
        self.write: Optional[MemoryObjectReceiveStream] = None
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # LLM 客户端实例
        self.llm_client = llm_client

    async def connect_to_server(self):
        """
        连接到 MCP 服务器。
        这里以 stdio 连接方式为例。
        """
        print(f"current working directory: {os.getcwd()}")
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py", "--transport", "stdio"],
            env={"UV_INDEX": os.environ.get("UV_INDEX", "")},
            cwd=os.getcwd(),
        )
        # 使用 AsyncExitStack 来统一管理多个异步上下文资源
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Clean up resources"""
        # 这里会依次退出 self.session，stdio_client 的上下文
        await self.exit_stack.aclose()

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        # 通过 MCP客户端 获取 MCP服务端 可用的 tools
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial LLM API call
        response = self.llm_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            # 将 MCP 的 tools 作为上下文传给 LLM 客户端
            tools=available_tools
        )

        # Process response and handle tool calls
        tool_results = []
        final_text = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call —— 调用 MCP 的 call_tool，并获取结果
                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Continue conversation with tool results
                if hasattr(content, 'text') and content.text:
                    messages.append({
                        "role": "assistant",
                        "content": content.text
                    })
                messages.append({
                    "role": "user",
                    "content": result.content
                })

                # Get next response from LLM
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")


async def run_mcp_client():
    llm_client = 'SomeLLM-Client'  # 这里应当使用 LLM 模型客户端实例
    client = MCPClient(llm_client)
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()


def main():
    asyncio.run(stdio_client_connect_usage())
    asyncio.run(run_mcp_client())


if __name__ == '__main__':
    main()
