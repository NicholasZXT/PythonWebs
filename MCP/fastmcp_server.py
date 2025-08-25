"""
练习 FastMCP 服务端使用
"""
from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel, Field
import asyncio
import click
from fastmcp import settings, FastMCP, Context
from logging_util import getLogger

logger = getLogger(name='mcp_server', debug=True, write_file=True)

fastmcp = FastMCP(
    name="HelpfulAssistant",
    instructions="This server provides data analysis tools. Call get_average() to analyze numerical data.",
    lifespan=None,
    auth=None,
    include_tags=None,
    exclude_tags=None,
    on_duplicate_tools="error",     # Handle duplicate registrations
    on_duplicate_resources="warn",
    on_duplicate_prompts="replace",
    include_fastmcp_meta=False,     # Disable FastMCP metadata for cleaner integration
)


# -------------- Tool ----------------
@fastmcp.tool(
    name="echo_tool",  # 工具名称，默认是函数名，此名称作为工具的唯一标识
    title="Echo Text Tool",  # 工具标题（可选），供用户查看
    description="""Echo the input text""",   # 工具描述（可选）
    tags={"echo"},
    meta={"version": "0.1"},
    enabled=True

)
async def echo_tool(
    text: str,
    # 被装饰的函数中，可以添加一个 Context 参数，Tool类会自动检测注入一个 Context 实例，用于访问当前MCP服务器的一些信息
    ctx: Context
) -> str:
    """Echo the input text"""
    logger.info(f"[Echo-Tool] echo: {text}")
    # 可以通过 Context 拿到的 MCP 服务器信息和功能如下：
    logger.info(f"[Echo-Tool] ctx.request_id: {ctx.request_id}")
    logger.info(f"[Echo-Tool] ctx.client_id: {ctx.client_id}")
    logger.info(f"[Echo-Tool] ctx.fastmcp: {ctx.fastmcp}")
    logger.info(f"[Echo-Tool] ctx.fastmcp.name: {ctx.fastmcp.name}")
    logger.info(f"[Echo-Tool] ctx.fastmcp.instructions: {ctx.fastmcp.instructions}")
    logger.info(f"[Echo-Tool] ctx.fastmcp.settings: {ctx.fastmcp.settings}")
    logger.info(f"[Echo-Tool] ctx.fastmcp.settings.host: {ctx.fastmcp.settings.host}")
    logger.info(f"[Echo-Tool] ctx.fastmcp.settings.port: {ctx.fastmcp.settings.port}")
    logger.info(f"[Echo-Tool] ctx.session: {ctx.session}")
    logger.info(f"[Echo-Tool] ctx.session.client_params: {ctx.session.client_params}")
    logger.info(f"[Echo-Tool] ctx.request_context: {ctx.request_context}")
    # Context 对象日志操作 —— 注意都是异步方法
    await ctx.info(f"[Echo-Tool] log info: {text}")
    await ctx.debug(f"[Echo-Tool] debug info: {text}")
    await ctx.warning(f"[Echo-Tool] warning info: {text}")
    await ctx.error(f"[Echo-Tool] error info: {text}")
    return text


@fastmcp.tool()
def get_weather(city: str) -> str:
    """获取天气信息"""
    return f"{city}的天气是晴天"


@fastmcp.tool()
def greet_user_tool(
    name: str = Field(description="The name of the person to greet"),
    title: str = Field(description="Optional title like Mr/Ms/Dr", default=""),
    times: int = Field(description="Number of times to repeat the greeting", default=1),
) -> str:
    """Greet a user with optional title and repetition"""
    greeting = f"Hello {title + ' ' if title else ''}{name}!"
    return "\n".join([greeting] * times)


# -------------- Resource ----------------
@fastmcp.resource(
    uri="echo://static",
    name='echo_resource',
    description="A static resource that always returns the same content",
)
def echo_resource() -> str:
    """Echo the input resource"""
    return "Echo!"


@fastmcp.resource(
    uri="greeting://{name}",
    name='greeting_resource',
    description="A resource that returns a personalized greeting",
)
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    logger.info(f"[Greeting-Resource] get_greeting: {name}")
    return f"Hello, {name}!"


@fastmcp.resource(
    uri="file://documents/{name}",
    name='file_resource',
    description="A resource that reads a document from disk",
)
def read_document(name: str) -> str:
    """Read a document by name."""
    # name: str = "document.txt"
    # This would normally read from disk
    return f"Content of {name}"


@fastmcp.prompt("echo")
def echo_prompt(text: str) -> str:
    """Echo the input prompt"""
    return text


@fastmcp.prompt()
def greet_user_prompt(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }
    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


@click.command()
@click.option("--transport", default="stdio", help="Transport protocol to use (stdio, sse, streamable-http)")
def main(transport: Literal["stdio", "sse", "streamable-http"]):
    logger.info(f'MCP Server starting with transport: {transport} ...')
    fastmcp.run(transport=transport)


if __name__ == '__main__':
    main()
