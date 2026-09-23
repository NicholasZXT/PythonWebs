"""
演示 MCP 服务端使用
"""
from typing import TYPE_CHECKING, Literal
from pydantic import BaseModel, Field
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
import click
from mcp import types
from mcp.server import FastMCP
# 下面的Server是更底层的组件，FastMCP里就封装了一个Server对象 —— 一般来说，不需要使用 Server
from mcp.server import Server  # 等价于 from mcp.server.lowlevel import Server
# 上面的 Server 底层依赖下面的 ServerSession —— 它底层直接基于 anyio 构建，而不是 starlette
from mcp.server.session import ServerSession
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.prompts import base as prompts_base
from mcp.server.fastmcp.tools import base as tools_base
from mcp.server.stdio import stdio_server
# from mcp.server.auth
from logging_util import getLogger

# 对于使用 stdio 方式的 MCP服务端来说，不能使用 print, logger 等向 stdout 打印字符串，因为服务端返回的 JSON-RPC 消息也会输出到stdout
# 被客户端作为消息读取，如果输出到 stdout，那么会破坏返回的 JSON-RPC 响应，导致客户端无法解析响应
logger = getLogger(name='mcp_server', debug=True, write_file=True)


# ------------ 模拟一个数据库 ------------
class Database:
    """Mock database class for example."""
    @classmethod
    async def connect(cls) -> "Database":
        """Connect to database."""
        return cls()

    async def disconnect(self) -> None:
        """Disconnect from database."""
        pass

    def query(self) -> str:
        """Execute a query."""
        return "Query result"


@dataclass
class AppContext:
    """Application context with typed dependencies."""
    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context."""
    # Initialize on startup
    db = await Database.connect()
    try:
        yield AppContext(db=db)
    finally:
        # Cleanup on shutdown
        await db.disconnect()


# -------------- 实例化 FastMCP ----------------
mcp = FastMCP(
    name="Introduction-MCP-Server",
    lifespan=app_lifespan,
    # 以下两个适用于 sse/streamable-http 启动方式，均为默认值
    host="127.0.0.1",
    port=8000,
)


# -------------- Tool ----------------
# 使用 @mcp.tool 装饰器来注册工具，底层实际上是调用 FastMCP.add_tool()  -> FastMCP._tool_manager.add_tool()
# 实际会封装为 mcp.server.fastmcp.tools.base.Tool 类实例
@mcp.tool(
    name="echo_tool",  # 工具名称，默认是函数名，此名称作为工具的唯一标识
    title="Echo Text Tool",   # 工具标题（可选），供用户查看
    description="""Echo the input text""",   # 工具描述（可选）
    annotations=None,   # 工具注解（可选）
    structured_output=None   # 输出结构化数据： None（默认）表示自动检测；True 表示（强制）返回结构化数据；False 表示返回非结构化数据
)
async def echo_tool(
    text: str,
    # 被装饰的函数中，可以添加一个 Context 参数，Tool类会自动检测注入一个 Context 实例，用于访问当前MCP服务器的一些信息
    # Context 是一个泛型类，有3个泛型参数：ServerSessionT, LifespanContextT, RequestT
    #  - ServerSessionT:    一般是 ServerSession 类
    #  - LifespanContextT:  用户自定义的 LifespanContext，一般是 @asynccontextmanager 注册的 lifespan 函数返回的对象
    #  - RequestT:          对应请求类，默认为 Request ？
    ctx: Context[ServerSession, AppContext]
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


@mcp.tool()
def get_weather(city: str) -> str:
    """获取天气信息"""
    return f"{city}的天气是晴天"


@mcp.tool()
def greet_user_tool(
    name: str = Field(description="The name of the person to greet"),
    title: str = Field(description="Optional title like Mr/Ms/Dr", default=""),
    times: int = Field(description="Number of times to repeat the greeting", default=1),
) -> str:
    """Greet a user with optional title and repetition"""
    greeting = f"Hello {title + ' ' if title else ''}{name}!"
    return "\n".join([greeting] * times)


# -------------- Resource ----------------
@mcp.resource(
    uri="echo://static",
    name='echo_resource',
    description="A static resource that always returns the same content",
)
def echo_resource() -> str:
    """Echo the input resource"""
    return "Echo!"


@mcp.resource(
    uri="greeting://{name}",
    name='greeting_resource',
    description="A resource that returns a personalized greeting",
)
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    logger.info(f"[Greeting-Resource] get_greeting: {name}")
    return f"Hello, {name}!"


@mcp.resource(
    uri="file://documents/{name}",
    name='file_resource',
    description="A resource that reads a document from disk",
)
def read_document(name: str) -> str:
    """Read a document by name."""
    # name: str = "document.txt"
    # This would normally read from disk
    return f"Content of {name}"


# -------------- Prompt ----------------
@mcp.prompt("echo")
def echo_prompt(text: str) -> str:
    """Echo the input prompt"""
    return text


@mcp.prompt()
def greet_user_prompt(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }
    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


@mcp.prompt(title="Debug Assistant")
def debug_error(error: str) -> list[prompts_base.Message]:
    return [
        prompts_base.UserMessage("I'm seeing this error:"),
        prompts_base.UserMessage(error),
        prompts_base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]


@click.command()
@click.option("--transport", default="stdio", help="Transport protocol to use (stdio, sse, streamable-http)")
def main(transport: Literal["stdio", "sse", "streamable-http"]):
    logger.info(f'MCP Server starting with transport: {transport} ...')
    mcp.run(transport=transport)


if __name__ == '__main__':
    main()
