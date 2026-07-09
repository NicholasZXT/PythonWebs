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
from langgraph.types import Command, GraphOutput
# %% =============== langchain组件 ===============
from langchain_core.language_models.chat_models import BaseChatModel, SimpleChatModel
from langchain_openai.chat_models import ChatOpenAI
from langchain_ollama.chat_models import ChatOllama
from langchain_core.messages import ChatMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage, FunctionMessage, ToolCall
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
    HumanInTheLoopMiddleware, TodoListMiddleware, InterruptOnConfig,
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
print(">>> API_KEY:", API_KEY)
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

    HumanInTheLoopMiddleware 的核心作用：
    当 Agent 准备调用某个工具时，中间件会暂停执行，等待人工做出决策后再继续。

    interrupt_on 参数支持以下形式：
    1. True (bool)  - 允许所有4种决策：approve / edit / reject / respond
    2. False (bool) - 自动放行，不触发中断（通常不写，默认不拦截）
    3. InterruptOnConfig (dict) - 精细控制，可指定：
       - allowed_decisions:  允许的决策类型列表
       - description:        自定义描述（str 或 callable）
       - when:               条件谓词，接收 ToolCallRequest，返回 True 才中断
       - args_schema:        编辑时的参数 JSON Schema

    四种决策类型 (DecisionType)：
    - approve : 批准，按原参数执行工具
    - edit    : 修改参数后执行
    - reject  : 拒绝执行，返回反馈给模型
    - respond : 人工直接回复，跳过工具执行（用于 ask_user 类工具）

    注意：HITL 依赖 LangGraph 的 checkpointer 持久化状态，必须配置 checkpointer 和 thread_id。
    """
    print("===> agent_middleware_hil_usage()")
    model = get_client_chat()

    # ========================================================================
    # 1. 定义 mock 工具（模拟各种需要审批的操作）
    # ========================================================================
    @tool(description="发送邮件给指定收件人")
    def send_email(to: str, subject: str, body: str) -> str:
        """模拟发送邮件"""
        return f"邮件已发送 -> 收件人: {to}, 主题: {subject}"

    @tool(description="删除数据库中的记录")
    def delete_records(table: str, condition: str) -> str:
        """模拟删除数据库记录"""
        return f"已从表 {table} 中删除记录，条件: {condition}"

    @tool(description="读取数据（安全操作，不需要审批）")
    def read_data(query: str) -> str:
        """模拟读取数据，安全操作"""
        return f"查询结果: [{{'id': 1, 'name': 'test'}}]"

    @tool(description="向用户询问有关习惯的问题，需要人工回复")
    def ask_user_hobit(question: str) -> str:
        """模拟向用户提问，实际由人工回答"""
        return f"用户回答了: {question}"

    # ========================================================================
    # 2. 构建 interrupt_on 配置，覆盖所有参数形式
    # ========================================================================
    # 自定义动态描述函数（展示 description 为 callable 的用法）
    def describe_send_email(tool_call: ToolCall, state: dict, runtime: Runtime) -> str:
        """根据工具调用参数动态生成审批描述"""
        args = tool_call["args"]
        return (
            f"⚠️ 邮件发送审批\n"
            f"收件人: {args.get('to', 'N/A')}\n"
            f"主题: {args.get('subject', 'N/A')}\n"
            f"正文: {args.get('body', 'N/A')}"
        )

    # 条件谓词：仅当删除条件不是 SELECT 时才触发中断（展示 when 的用法）
    def is_dangerous_delete(request: ToolCallRequest) -> bool:
        """当删除操作不是基于子查询时，需要人工审批"""
        condition = request.tool_call["args"].get("condition", "")
        # 如果条件中包含 SELECT 子查询，说明是精确删除，自动放行
        if "SELECT" in condition.upper():
            return False
        return True

    # 组装 interrupt_on 字典 —— 展示所有参数形式：
    # - send_email:     True → 全部4种决策可用 + 自定义动态 description
    # - delete_records: InterruptOnConfig → 只允许 approve/reject + when 条件谓词
    # - ask_user_hobit: InterruptOnConfig → 只允许 respond（人工直接回答）
    # - read_data:      False → 安全操作，不触发中断
    interrupt_on: dict[str, bool | InterruptOnConfig] = {
        # 注意：key 必须与工具函数名完全一致！
        # 形式1: True - 允许所有4种决策（approve/edit/reject/respond）+ 自定义动态描述
        "send_email": {
            "allowed_decisions": ["approve", "edit", "reject", "respond"],
            "description": describe_send_email,  # callable 动态描述
        },
        # 形式2: InterruptOnConfig - 只允许 approve 和 reject，不允许编辑
        "delete_records": {
            "allowed_decisions": ["approve", "reject"],
            "description": "⚠️ 数据库删除操作需要审批",  # 静态字符串描述
            "when": is_dangerous_delete,  # 条件谓词：仅危险删除才中断
        },
        # 形式3: InterruptOnConfig - 只允许 respond（人工回答），工具本身不执行
        "ask_user_hobit": {
            "allowed_decisions": ["respond"],
            "description": "请回答Agent的问题",
        },
        # 形式4: False - 自动放行，这些工具不会触发中断
        "read_data": False,
    }

    # ========================================================================
    # 3. 创建 Agent（必须配置 checkpointer）
    # ========================================================================
    checkpointer = MemorySaver()  # 生产环境应使用 AsyncPostgresSaver

    agent: CompiledStateGraph = create_agent(
        name="HITL-Demo-Agent",
        model=model,
        system_prompt="你是一个需要经过审批才能执行敏感操作的助手。",
        tools=[send_email, delete_records, read_data, ask_user_hobit],
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on=interrupt_on,
                description_prefix="工具执行需要审批",
            ),
        ],
        checkpointer=checkpointer,
    )

    # ========================================================================
    # 4. 场景演示：发送邮件 → 触发中断 → 人工 approve
    # ========================================================================
    print("\n" + "=" * 60)
    print("【场景1】发送邮件 → 触发中断 → 人工 approve")
    print("=" * 60)

    config = {"configurable": {"thread_id": "hil-demo-1"}}

    # 首次调用：Agent 会尝试调用 send_email，触发 HITL 中断
    # 提示词要明确指令模型直接调用工具，避免模型先"问"而不调用
    result: GraphOutput = agent.invoke(
        input={
            "messages": HumanMessage(
                content="请立即调用 send_email 工具发送邮件给 admin@example.com，"
                        "主题是'系统维护通知'，内容是'明天凌晨2点系统维护'。不要询问，直接调用工具。"
            ),
        },
        config=config,
        version="v2",  # v2 返回 GraphOutput，包含 .interrupts 属性
    )

    # 检查是否触发了中断：interrupts 无中断时为空元组 ()，有中断时包含 Interrupt 对象
    interrupted = bool(result.interrupts)
    print(f"\n>>> 是否中断: {interrupted}")
    if interrupted:
        for i, interrupt_val in enumerate(result.interrupts):
            print(f"\n--- 中断 {i + 1} ---")
            hitl_value = interrupt_val.value
            print(f"待审批操作:")
            for j, action_req in enumerate(hitl_value["action_requests"]):
                print(f"  [{j}] 工具: {action_req['name']}")
                print(f"      参数: {action_req['args']}")
                print(f"      描述: {action_req.get('description', 'N/A')}")
            print(f"允许的决策: {hitl_value['review_configs']}")

        # 人工决策：approve 批准执行
        print("\n>>> 人工决策: approve (批准执行)")
        result2 = agent.invoke(
            # resume 传入的dict里，必须要有 decisions key，并且是一个数组
            Command(resume={"decisions": [{"type": "approve"}]}),
            config=config,
            version="v2",
        )
        print("\n最终回复:")
        # v2 模式下，result2 是 GraphOutput，消息在 result2.value["messages"] 中
        for msg in result2.value.get("messages", []):
            if isinstance(msg, AIMessage) and msg.content:
                print(f"  AI: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"  Tool[{msg.name}]: {msg.content}")

    # ========================================================================
    # 5. 场景演示：删除记录 → 触发中断 → 人工 reject
    # ========================================================================
    print("\n" + "=" * 60)
    print("【场景2】删除记录 → 触发中断 → 人工 reject（拒绝）")
    print("=" * 60)

    config2 = {"configurable": {"thread_id": "hil-demo-2"}}

    result = agent.invoke(
        input={
            "messages": HumanMessage(
                content="请立即调用 delete_records 工具，删除 users 表中所有 status='inactive' 的记录。"
                        "直接调用工具，不要先询问。"
            ),
        },
        config=config2,
        version="v2",
    )

    interrupted = bool(result.interrupts)
    print(f"\n>>> 是否中断: {interrupted}")
    if interrupted:
        for interrupt_val in result.interrupts:
            hitl_value = interrupt_val.value
            for action_req in hitl_value["action_requests"]:
                print(f"  待审批: {action_req['name']} -> {action_req['args']}")
            print(f"  允许的决策: {hitl_value['review_configs'][0]['allowed_decisions']}")

        # 人工决策：reject 拒绝，并给出反馈
        print("\n>>> 人工决策: reject (拒绝，因为条件太宽泛)")
        result2 = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "type": "reject",
                            "message": "拒绝：条件太宽泛，可能误删。请使用更精确的条件（如指定具体ID）。",
                        }
                    ]
                }
            ),
            config=config2,
            version="v2",
        )
        print("\n最终回复:")
        for msg in result2.value.get("messages", []):
            if isinstance(msg, AIMessage) and msg.content:
                print(f"  AI: {msg.content}")

    # ========================================================================
    # 6. 场景演示：条件谓词 when 的效果 —— 安全的删除自动放行
    # ========================================================================
    print("\n" + "=" * 60)
    print("【场景3】when 条件谓词：基于子查询的删除 → 自动放行，不触发中断")
    print("=" * 60)

    config3 = {"configurable": {"thread_id": "hil-demo-3"}}

    result = agent.invoke(
        input={
            "messages": HumanMessage(
                content="请立即调用 delete_records 工具，删除 users 表中 "
                        "id 在 (SELECT id FROM temp_users) 中的记录。直接调用工具。"
            ),
        },
        config=config3,
        version="v2",
    )

    interrupted = bool(result.interrupts)
    print(f"\n>>> 是否中断: {interrupted}")
    if not interrupted:
        print(">>> 未触发中断！因为 when 谓词判断此操作为安全操作（含 SELECT 子查询），自动放行。")
        for msg in result.value["messages"]:
            if isinstance(msg, AIMessage) and msg.content:
                print(f"  AI: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"  Tool[{msg.name}]: {msg.content}")

    # ========================================================================
    # 7. 场景演示：ask_user 工具 → respond 决策（人工直接回答）
    # ========================================================================
    print("\n" + "=" * 60)
    print("【场景4】ask_user_hobit 工具 → 触发中断 → 人工 respond（人工回答代替工具执行）")
    print("=" * 60)

    config4 = {"configurable": {"thread_id": "hil-demo-4"}}

    result = agent.invoke(
        input={
            "messages": HumanMessage(
                content="你需要收集用户偏好。请立即调用 ask_user_hobit 工具，传递参数 question='你更喜欢蓝色还是绿色？'。"
                        "直接调用工具，不要先解释。"
            ),
        },
        config=config4,
        version="v2",
    )

    interrupted = bool(result.interrupts)
    print(f"\n>>> 是否中断: {interrupted}")
    if interrupted:
        for interrupt_val in result.interrupts:
            hitl_value = interrupt_val.value
            for action_req in hitl_value["action_requests"]:
                print(f"  待审批: {action_req['name']} -> {action_req['args']}")
            print(f"  允许的决策: {hitl_value['review_configs'][0]['allowed_decisions']}")

        # respond: 人工直接回答，工具本身不执行，回答内容作为 ToolMessage 返回
        print("\n>>> 人工决策: respond (人工回答'蓝色'，跳过工具执行)")
        result2 = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "type": "respond",
                            "message": "蓝色",
                        }
                    ]
                }
            ),
            config=config4,
            version="v2",
        )
        print("\n最终回复:")
        for msg in result2.value.get("messages", []):
            if isinstance(msg, AIMessage) and msg.content:
                print(f"  AI: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"  ToolMessage[{msg.name}]: {msg.content}")

    # ========================================================================
    # 8. 场景演示：edit 决策 —— 修改工具参数后执行
    # ========================================================================
    print("\n" + "=" * 60)
    print("【场景5】发送邮件 → 触发中断 → 人工 edit（修改收件人后执行）")
    print("=" * 60)

    config5 = {"configurable": {"thread_id": "hil-demo-5"}}

    result = agent.invoke(
        input={
            "messages": HumanMessage(
                content="请立即调用 send_email 工具，发送邮件给 user@test.com，"
                        "主题'测试'，内容'这是一封测试邮件'。直接调用工具。"
            ),
        },
        config=config5,
        version="v2",
    )

    interrupted = bool(result.interrupts)
    print(f"\n>>> 是否中断: {interrupted}")
    if interrupted:
        for interrupt_val in result.interrupts:
            hitl_value = interrupt_val.value
            for action_req in hitl_value["action_requests"]:
                print(f"  原始参数: {action_req['args']}")

        # edit: 修改参数（如更换收件人）
        print("\n>>> 人工决策: edit (修改收件人为 supervisor@example.com)")
        result2 = agent.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "type": "edit",
                            "edited_action": {
                                "name": "send_email",
                                "args": {
                                    "to": "supervisor@example.com",
                                    "subject": "测试",
                                    "body": "这是一封测试邮件",
                                },
                            },
                        }
                    ]
                }
            ),
            config=config5,
            version="v2",
        )
        print("\n最终回复:")
        for msg in result2.value.get("messages", []):
            if isinstance(msg, AIMessage) and msg.content:
                print(f"  AI: {msg.content}")
            elif isinstance(msg, ToolMessage):
                print(f"  Tool[{msg.name}]: {msg.content}")

    print("\n" + "=" * 60)
    print("=== HumanInTheLoopMiddleware 所有 interrupt_on 形式演示完毕 ===")
    print("=" * 60)



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
    # auto_agent_usage()
    agent_middleware_hil_usage()
    # asyncio.run(auto_agent_with_mcp_usage())

if __name__ == "__main__":
    main()
