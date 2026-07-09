"""
LangChain-Agent实践。
主要包含两个方面的内容：
1. LangChain-v1.0 提供的 create_agent() 函数 + AgentMiddleware 使用研究实践。
2. LangChain 官方提供的 deepagents 包的使用。
"""
# %%
import os
import asyncio
from typing import Optional, Dict, List, Union, Any, Callable, cast, TypeAlias
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel, Field
from dataclasses import dataclass
# %% =============== v1.0版本Agent底层是借助的LangGraph组件 ===============
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
# %% =============== langchain组件 ===============
from langchain_core.language_models.chat_models import BaseChatModel, SimpleChatModel
from langchain_openai.chat_models import ChatOpenAI
from langchain_ollama.chat_models import ChatOllama
from langchain_core.messages import ChatMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage, FunctionMessage
from langchain_core.tools import BaseTool, BaseToolkit, Tool, StructuredTool, tool, InjectedToolArg, ToolException
from langchain.tools import InjectedState, InjectedStore, ToolRuntime
from langchain.tools.tool_node import ToolCallRequest
# ---------- langchain-v1.0 新增的 agent 抽象 ----------
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
# ---------- middleware，v1.0版本一个更新亮点 ----------
from langchain.agents.middleware import (
    AgentMiddleware, AgentState, ModelRequest, ModelResponse,
    before_agent, after_agent, before_model, after_model, wrap_model_call, wrap_tool_call, hook_config
)
# 自带的 middleware 实现
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware, TodoListMiddleware,
    SummarizationMiddleware, ModelCallLimitMiddleware, ToolCallLimitMiddleware,
)
# %% =============== deepagents组件 ===============
from deepagents import (
    create_deep_agent, CompiledSubAgent, SubAgent, AsyncSubAgent,
    SubAgentMiddleware, AsyncSubAgentMiddleware, MemoryMiddleware, FilesystemMiddleware, FilesystemPermission
)
# %% =============== v1.0版本 Auto-Agent 搭配 MCP ===============
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langchain_mcp_adapters.callbacks import Callbacks, CallbackContext, ProgressCallback, LoggingMessageCallback
# from mcp.types import LoggingMessageNotificationParams

# %% ===================================================================================================================
API_KEY = os.getenv('API_KEY', 'EMPTY')
print(f">>> API_KEY:", API_KEY)
# --- Ollama 本地部署 ---
# LLM_URL = 'http://localhost:11434'
# MODEL = 'qwen2.5:7b'
# MODEL = 'qwen3:8b'
# MODEL = 'qwen2.5:14b'
# MODEL = 'qwen3:14b'
# --- 在线模型服务 ---
# LLM_URL = 'https://api.deepseek.com'  # DeepSeek
# LLM_URL = 'https://ark.cn-beijing.volces.com/api/v3'  # 火山引擎
LLM_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1'  # 阿里百炼
MODEL = 'deepseek-v4-flash'
# MODEL = 'deepseek-v4-pro'
# --- vLLM 部署 ---
# LLM_URL = 'http://172.16.0.32:10086/v1'
# MODEL = 'Qwen2.5-32B'
# MODEL = 'Qwen3-32B'


# %% --------- 工具函数，方便后续使用LLM/ChatLLM --------
def get_client_chat() -> Union[BaseChatModel, SimpleChatModel]:
    client_chat = ChatOpenAI(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        # temperature=0.7,
        # top_p=1,
        # streaming=False,
    )
    # client_chat = ChatOllama(
    #     base_url=LLM_URL,
    #     model=MODEL,
    #     # temperature=0.7,
    #     # top_p=1,
    #     keep_alive='30m',
    #     # 控制模型是否进行think，只对支持think的模型有效，但是似乎对 qwen3 的think模式无效
    #     think=False
    # )
    print(f"{'-'*55}\n===> Using model '{MODEL}' with {client_chat.get_name()}\n{'-'*55}")
    return client_chat


# %% ======================= LangChain v1.x 的 Agent 使用 =======================
MyResponse: TypeAlias = Dict[str, Any]

def auto_agent_usage():
    """
    展示 LangChain-v1.x 的 Agent 使用。
    """
    print("===> auto_agent_usage()")
    model = get_client_chat()

    memory_saver = MemorySaver()
    memory_store = InMemoryStore()
    memory_store.put(namespace=("user", "db"), key="XiaoMing", value={"age": 20, "gender": "male"})
    memory_store.put(namespace=("user", "db"), key="XiaoHong", value={"age": 18, "gender": "female"})

    @dataclass
    class UserContext:
        """定义 AgentMiddleware 泛型里的 ContextT 泛型类型的具体类"""
        user_name: str

    class MyAgentState(AgentState[MyResponse]):
        """
        Graph State 表示类，必须要继承自 AgentState 类，本质上是一个 TypedDict。
        它是一个 base schema，后续所有middleware里定义的schema都会被合并到这个base schema里
        """
        base_state: str

    # class ModelHookState(AgentState):
    class ModelHookState(MyAgentState):
        """
        ModelHook 中间件的 state_schema.
        虽然可以直接继承 AgentState，但是建议继承自 MyAgentState，因为所有中间件的state_schema的属性会被合并到 MyAgentState 里。
        """
        model_hook_state: str

    class AgentHook(AgentMiddleware[MyAgentState, UserContext, MyResponse]):
        """
        自定义中间件，展示 before_agent / after_agent 两个 hook 方法的使用。
        """
        # 显式设置当前中间件使用的 StateSchema 类，不过不设置似乎也没事。
        state_schema = MyAgentState
        # tools = []
        # transformers = ()

        def before_agent(self, state: MyAgentState, runtime: Runtime[UserContext]) -> dict[str, Any] | None:
            """
            :param state: 传入的是 state 对象
            :param runtime: 底层LangGraph提供的 Runtime[ContextT] 泛型dataclass类，用于获取LangGraph运行时的上下文。
            :return:
            """
            print(f"--> before_agent called with context: {runtime.context}...")
            # print(f"   before_agent state.__class__: {type(state)}")  # <class 'dict'>
            print(f"    before_agent state.keys: {state.keys()}")
            # 如果想更新状态里的某个 key ，不要直接更新，应当返回一个 dict，key就是要更新的状态的key
            # state["base_state"] += ";before_agent"
            base_state_update = state["base_state"] + ";before_agent"
            return {'base_state': base_state_update}

        def after_agent(self, state: MyAgentState, runtime: Runtime[UserContext]) -> dict[str, Any] | None:
            print(f"<-- after_agent called with context: {runtime.context}...")
            # print(f"   after_agent state.__class__: {type(state)}")  # <class 'dict'>
            print(f"    after_agent state.keys: {state.keys()}")
            # state["base_state"] += ";after_agent"
            base_state_update = state["base_state"] + ";after_agent"
            return {'base_state': base_state_update}

    class ModelHook(AgentMiddleware[ModelHookState, UserContext, MyResponse]):
        """
        自定义中间件，展示 before_model / after_model 两个 hook 方法的使用。
        """
        # 这个 Middleware 也定义了自己的 state_schema
        state_schema = ModelHookState

        def before_model(self, state: ModelHookState, runtime: Runtime[UserContext]) -> dict[str, Any] | None:
            print(f"  --> before_model called with context: {runtime.context}...")
            # print(f"    before_model state.__class__: {type(state)}")
            print(f"      before_model state.keys: {state.keys()}")
            print(f"      before_model called with state.base_state: {state.get('base_state', None)}")
            model_state_hook_update = state["model_hook_state"] + ";before_model"
            return {'model_hook_state': model_state_hook_update}

        def after_model(self, state: ModelHookState, runtime: Runtime[UserContext]) -> dict[str, Any] | None:
            print(f"  <-- after_model called with context: {runtime.context}...")
            # print(f"      after_model state.__class__: {type(state)}")
            print(f"      after_model state.keys: {state.keys()}")
            print(f"      after_model called with state.base_state: {state.get('base_state', None)}")
            model_state_hook_update = state["model_hook_state"] + ";after_model"
            return {'model_hook_state': model_state_hook_update}

    class WrapModelHook(AgentMiddleware[MyAgentState, UserContext, MyResponse]):
        """
        自定义中间件，展示 wrap_model_call hook 方法的使用。
        wrap_model_call 和 下面的 wrap_tool_call 这两个 hook 方法的函数签名和上面的不一样。
        """
        def wrap_model_call(
            self,
            request: ModelRequest,
            handler: Callable[[ModelRequest], ModelResponse],
        ) -> ModelResponse | AIMessage:
            """
            :param request: 待执行的 ModelRequest，包含了 state 和 runtime 。
            :param handler: 下一个中间件的 hook 方法。因此可以在当前中间件中实现：决定是否继续调用后续中间件、是否重试等逻辑。
            :return:
            """
            print(f"    <--> wrap_model_call called with context: {request.runtime.context}...")
            # print(f"         wrap_model_call state.__class__: {type(request.state)}")
            print(f"         wrap_model_call state.keys: {request.state.keys()}")
            print(f"         wrap_model_call called with state.base_state: {request.state.get('base_state', None)}")
            return handler(request)

    class WrapToolHook(AgentMiddleware[MyAgentState, UserContext, MyResponse]):
        """
        自定义中间件，展示 wrap_tool_call hook 方法的使用。
        """
        def wrap_tool_call(
            self,
            request: ToolCallRequest,
            handler: Callable[[ToolCallRequest], ToolMessage | Command],
        ) -> ToolMessage | Command:
            print(f"    <--> wrap_tool_call called with context: {request.runtime.context}...")
            # print(f"         wrap_tool_call state.__class__: {type(request.state)}")
            print(f"         wrap_tool_call state.keys: {request.state.keys()}")
            print(f"         wrap_tool_call called with state.base_state: {request.state.get('base_state', None)}")
            return handler(request)

    @tool(description="获取当前Agent的执行上下文")
    def get_agent_context(runtime: ToolRuntime[UserContext]) -> str:
        # 从自定义的 UserContext 里获取用户名
        user_name = runtime.context.user_name
        # 然后从store里获取用户信息
        user_info = runtime.store.get(namespace=("user", "db"), key=user_name)
        result = f"当前的Agent执行上下文是：{user_name} -> {user_info}"
        return result

    @tool(description="获取某个城市的天气信息")
    def get_weather(city: str) -> str:
        result = f"{city}的天气是晴天"
        return result

    # ---------- 构建 Agent -----------
    agent: CompiledStateGraph = create_agent(
        name="Some-Agent",
        model=model,
        system_prompt="你是一个智能助手",
        tools=[get_agent_context, get_weather],
        middleware=[AgentHook(), ModelHook(), WrapModelHook(), WrapToolHook()],
        state_schema=MyAgentState,
        context_schema=UserContext,
        checkpointer=memory_saver,
        store=memory_store,
        response_format=None,
        # interrupt_before=None,
        # interrupt_after=None,
        # debug=True
    )
    # 查看图结构
    # from .langgraph_practice import show_graph
    # show_graph(agent)

    print('************** Agent-Chat-Round-1 **************')
    agent_response = agent.invoke(
        # input输入的dict必须对应初始化时传入的state_schema，这里是 MyAgentState；
        # 此外，还可以传入各个Middleware的state_schema里的key
        input={
            "messages": HumanMessage(content="北京的天气如何？"),  # messages 这个key是 AgentState 定义的
            "base_state": "base_state_init",                    # base_state 这个key是 MyAgentState 定义的
            "model_hook_state": "model_hook_state_init",        # model_hook_state 这个key是 ModelHookState 定义的
        },
        config={"configurable": {"thread_id": "t1"}},
        context=UserContext(user_name="XiaoMing")
    )
    # print(type(agent_response))   # <class 'dict'>
    # print(agent_response.keys())  # dict_keys(['messages', 'model_hook_state', 'base_state'])
    # print(agent_response)
    print("agent response messages:")
    for msg in agent_response['messages']:
        msg.pretty_print()
    print("-----------------------------------------")
    print("agent response base_state: ", agent_response['base_state'])
    print("agent response model_hook_state: ", agent_response['model_hook_state'])

    print('\n************** Agent-Chat-Round-2 **************')
    agent_response = agent.invoke(
        input={
            "messages": HumanMessage(content="当前Agent的运行上下文是什么？"),
            "base_state": "base_state_init",
            "model_hook_state": "model_hook_state_init",
        },
        config={"configurable": {"thread_id": "t2"}},
        context=UserContext(user_name="XiaoHong")
    )
    print("agent response messages:")
    for msg in agent_response['messages']:
        msg.pretty_print()
    print("-----------------------------------------")
    print("agent response base_state: ", agent_response['base_state'])
    print("agent response model_hook_state: ", agent_response['model_hook_state'])


# %% ======================= LangChain v1.x 内置Middleware使用研究 =======================
def agent_middleware_hil_usage():
    """
    展示 HumanInTheLoopMiddleware 使用。
    :return:
    """
    print("===> agent_middleware_hil_usage()")
    model = get_client_chat()

    memory_saver = MemorySaver()

    def read_email(email_name: str) -> str:
        """Mock function to read an email by its name."""
        return f"Email content for ID: {email_name}"

    def your_send_email_tool(recipient: str, subject: str, body: str) -> str:
        """Mock function to send an email."""
        return f"Email sent to {recipient} with subject '{subject}'"

    # 此中间件实现的是 after_model hook 方法。
    hil_middleware = HumanInTheLoopMiddleware(
        # 接受一个dict，key 是工具名称，value是该工具的HIL配置
        interrupt_on={
            "your_read_email_tool": False,
            "your_send_email_tool": {
                "allowed_decisions": ["approve", "edit", "reject"],
            },
        }
    )

    agent = create_agent(
        model=model,
        tools=[your_read_email_tool, your_send_email_tool],
        checkpointer=memory_saver,
        middleware=[hil_middleware],
    )


# %% ======================= LangChain v1.x Auto-Agent 配合 MCP 使用 =======================
async def auto_agent_with_mcp_usage() -> None:
    """
    展示 LangChain v1.x auto agent 配合 MCP 使用。
    """
    print("===> Auto-agent with MCP usage")

    # 定义 2个 MCP 回调函数
    # 查看源码可以发现，这两个回调函数不是在MCP客户端使用的，而是传递给 MCP Session 使用的 --------------------- KEY
    # 而且在 0.1.14 版本，似乎只有 on_logging_message 回调函数会被传递给 MCP Session,
    # on_progress 这个回调函数没有被使用
    async def on_logging_message(
        params: LoggingMessageNotificationParams,
        context: CallbackContext,
    ) -> None:
        """
        Handle log messages from MCP servers.
        此回调函数必须满足 MCP 回调函数 Protocol: LoggingMessageCallback
        """
        print(f"[MCP.callback.on_logging_message] [{context.server_name}] {params.level}: {params.data}")

    async def on_progress(
        progress: float,
        total: float | None,
        message: str | None,
        context: CallbackContext,
    ) -> None:
        """
        Handle progress updates from MCP servers.
        此回调函数必须满足 MCP 回调函数 Protocol: ProgressCallback
        """
        percent = (progress / total * 100) if total else progress
        tool_info = f" ({context.tool_name})" if context.tool_name else ""
        print(f"[MCP.callback.on_progress] [{context.server_name}{tool_info}] Progress: {percent:.1f}% - {message}")

    # 初始化 MCP 客户端
    mcp_client = MultiServerMCPClient(
        connections={
            # STDIO 模式
            # "weather": {
            #     "transport": "stdio",  # Local subprocess communication
            #     "command": "python",
            #     # Absolute path to your math_server.py file
            #     "args": ["/path/to/math_server.py"],
            # },
            # HTTP 模式，配合 simple_mcp_server.py 使用
            "weather": {
                "transport": "streamable_http",  # HTTP-based remote server
                "url": "http://localhost:8000/mcp",
            }
        },
        # 回调函数，目前只支持两种作用的回调函数，在 v0.1.14 版本中，只有 on_logging_message 回调函数实际有用，并且是在 MCP Session 中使用的
        callbacks=Callbacks(on_logging_message=on_logging_message, on_progress=on_progress),
        tool_interceptors=None
    )
    # 获取 MCP 工具，这些工具会被转换成 LangChain 的 Tool 对象
    mcp_tools: List[BaseTool] = await mcp_client.get_tools()
    print("******************************************")
    print("MCP tools:")
    for tool in mcp_tools:
        print(tool)

    # 正常创建 Agent
    print("******************************************")
    print("creating agent with MCP tools...")
    model = get_client_chat()
    memory_saver = MemorySaver()
    memory_store = InMemoryStore()
    agent: CompiledStateGraph = create_agent(
        name="Some-Agent-With-MCP",
        model=model,
        system_prompt="你是一个智能助手",
        tools=mcp_tools,
        middleware=(),
        checkpointer=memory_saver,
        store=memory_store,
        response_format=None,
        state_schema=None,
        context_schema=None,
        # interrupt_before=None,
        # interrupt_after=None,
        # debug=True
    )

    print("******************************************")
    print("agent invoke with MCP tools...")
    agent_response = await agent.ainvoke(
        input={
            "messages": HumanMessage(content="北京的天气如何？"),
        },
        config={"configurable": {"thread_id": "t1"}}
    )
    print("agent response messages:")
    for msg in agent_response['messages']:
        msg.pretty_print()




def main():
    """运行入口"""
    auto_agent_usage()
    # asyncio.run(auto_agent_with_mcp_usage())

if __name__ == "__main__":
    main()
