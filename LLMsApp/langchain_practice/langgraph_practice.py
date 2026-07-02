"""
简单研究 LangGraph 的使用 —— 适用于 v0.6.x / v1.x 版本。

主要参考了如下官方文档：
- [LangGraph Glossary](https://langchain-ai.github.io/langgraph/concepts/low_level/)
- [LangGraph Quickstart](https://langchain-ai.github.io/langgraph/tutorials/introduction/)

首先需要明确的是，LangGraph 不依赖 Langchain-Core 或者 Langchain，因此下面的研究都使用一个简单的Python Callable 对象
来代替实际中的 Langchain-Core/Langchain 里的 Runnable/LLM/ChatModel/Chain 对象。

即使升级到 LangGraph v1.0.x 版本，LangGraph 的核心架构和组件都没有太大的变化。
"""
# %%
from typing import Annotated, List, TypedDict, Dict, Union, Iterator
from dataclasses import dataclass
# from typing_extensions import TypedDict
import time
import asyncio
# ---------- LangGraph Graph 组件 ----------
from langgraph.constants import START, END
# from langgraph.graph.graph import Graph, CompiledGraph  # 这两个类只有 v0.4.10 版本之前有，v0.5.0开始被删除了
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import MessageGraph, MessagesState, add_messages
# --- Functional API ---
from langgraph.func import entrypoint, task
# ---------- LangGraph Memory/Store 组件 ----------
from langgraph.checkpoint.base import CheckpointTuple, Checkpoint, CheckpointMetadata, BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.config import get_store, get_stream_writer
from langgraph.types import StateSnapshot
# ---------- LangGraph Tool 组件 ----------
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent, InjectedState, InjectedStore, ToolCallTransformer
from langgraph.runtime import Runtime
from langchain.tools import ToolRuntime  # LangChain 里也提供了一个类似的 ToolRuntime 类
from langgraph.utils.runnable import RunnableCallable
# --- EventStream ---
from langgraph.stream import StreamChannel, StreamTransformer, ProtocolEvent, GraphRunStream
# from langgraph.prebuilt.chat_agent_executor import AgentState
# ---------- LangGraph HIL工具 & 容错处理 ----------
from langgraph.types import (
    interrupt, Command, Send,
    default_retry_on, RetryPolicy, TimeoutPolicy,
    StreamWriter,
)
from langgraph.errors import GraphDrained, NodeError, NodeTimeoutError
# ---------- langchain-core 组件 ----------
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.schema import StreamEvent
from langchain_core.language_models.chat_models import BaseChatModel, SimpleChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai.chat_models import ChatOpenAI
from langchain_ollama.chat_models import ChatOllama
from langchain_core.tools import BaseTool, StructuredTool, tool
# ---------- 其他依赖 ----------
import json

# --- vLLM 部署 ---
# API_KEY = 'Empty'
# LLM_URL = 'http://172.16.0.32:10086/v1'
# MODEL = 'Qwen2.5-32B-Instruct'
# --- Ollama 本地部署 ---
API_KEY = 'Empty'
LLM_URL = 'http://localhost:11434'
MODEL = 'qwen2.5:7b'
# MODEL = 'qwen3:8b'

# %%
def get_client_chat() -> Union[BaseChatModel, SimpleChatModel]:
    # client_chat = ChatOpenAI(
    #     openai_api_key=API_KEY,
    #     openai_api_base=LLM_URL,
    #     model_name=MODEL,
    #     # temperature=0.7,
    #     # top_p=1,
    #     # streaming=False,
    # )
    client_chat = ChatOllama(
        base_url=LLM_URL,
        model=MODEL,
        # temperature=0.7,
        # top_p=1,
        keep_alive='30m'
    )
    return client_chat


# %% ======================= 无状态图 构建 =======================
def stateless_graph_usage():
    """
    Graph / CompiledGraph 只有 v0.4.10 版本之前有，v0.5.0 版本开始删除了这两个类所在的 langgraph.graph.graph.py 文件.
    因此这两个类不需要关注了。
    """
    ...
    # 创建一个 Graph，这个Graph类不接受任何初始化参数，所以说它是无状态的。
    # graph = Graph()
    # 定义节点
    # graph.add_node(node="hello", action=lambda _: "Hello, world !")
    # graph.add_node(node="welcome", action=lambda _: "Welcome LangGraph !")
    # graph.add_node(node="bye", action=lambda _: "Goodbye !")

    # 定义边
    # graph.add_edge("hello", "welcome")
    # graph.add_edge("welcome", "bye")

    # 定义起始点和结束点
    # graph.set_entry_point('hello')
    # graph.set_finish_point('bye')

    # 编译并执行
    # compile_graph: CompiledGraph = graph.compile(name='StatelessGraph')
    # print(compile_graph.config_specs)
    # print(compile_graph.config_type)
    # result = compile_graph.invoke(input={'key1': 'value1', 'key2': 'value2'})
    # print(result)


# %% ======================= 简单有状态图 构建 =======================
def stateful_graph_usage():
    """
    LangGraph 的 StateGraph 基本使用
    """
    # 1. 首先定义整个 Graph 的状态表示，可以直接用dict，也可以用 TypedDict，或者是 Pydantic的 BaseModel —— 状态表示完全由用户自定义
    class SimpleState(TypedDict):
        """
        这个 state 对象的 key 就是后续 invoke() 方法里 input 参数接受的 dict 的key
        """
        messages: List[str]
        count: int

    # 2. 定义Node里要运行的Python函数
    def greet_node(state: SimpleState) -> SimpleState:
        print(f"--> greet_node start...")
        print(f"  state: {state}")
        state["messages"].append("Hello")
        print(f"<-- greet_node end.")
        return state

    def increment_node(state: SimpleState) -> SimpleState:
        print(f"--> increment_node start...")
        print(f"  state: {state}")
        state["count"] += 1
        print(f"<-- increment_node end.")
        return state

    def something_node(state: SimpleState) -> SimpleState:
        print(f"--> something_node start...")
        print(f"  state: {state}")
        state["messages"].append("Something")
        state["count"] += 2
        print(f"<-- something_node end.")
        return state

    def partial_node(state: SimpleState) -> Dict[str, int]:
        print(f"--> partial_node start...")
        print(f"  state: {state}")
        print(f"<-- partial_node end.")
        # 只返回状态部分的key也可以，不过此时如果对应的 key 没有设置 reducer 函数的话，默认会覆盖该 key 的内容
        return {'count': 10}

    # 3. 使用StateGraph 构建 Graph，初始化参数必须传入自定义的 State 类
    # state_schema 指定的 State 类，对应的就是 invoke() 方法里 input= 参数的 dict 结构 -------------------- KEY
    graph = StateGraph(state_schema=SimpleState)

    # 4. 使用 add_node 方法添加节点，add_node 方法有多个重载，注意选择
    graph.add_node(node="greet_node", action=greet_node)
    graph.add_node(node="increment_node", action=increment_node)
    graph.add_node(node="something_node", action=something_node)
    graph.add_node(node="partial_node", action=partial_node)

    # 5. 定义边
    graph.set_entry_point("greet_node")
    graph.add_edge("greet_node", "increment_node")
    graph.add_edge("increment_node", "something_node")
    graph.add_edge("something_node", "partial_node")
    graph.set_finish_point("partial_node")

    # 6. 编译构建 Graph，返回的是 CompiledStateGraph 对象
    compile_graph: CompiledStateGraph = graph.compile(name='SimpleStateGraph')
    # 可以查看具体的图结构
    # graph_picture = compile_graph.get_graph()
    print(compile_graph.config_specs)
    print(compile_graph.name)
    # print(compile_graph.get_name())

    # 7. 使用 Graph
    # 运行Graph: 调用 invoke/ainvoke; stream/astream 方法
    # invoke()方法的 input= 参数接受一个 TypedDict/dataclass/pydantic BaseModel，对应于初始化时 state_schema 定义的结构 ------ KEY
    input = {"messages": [], "count": 0}
    print(f"Graph input: {input}")
    res = compile_graph.invoke(input=input)
    print(type(res))  # 早期版本是 <class 'langgraph.pregel.io.AddableValuesDict'>，新版本是 <class 'dict'>
    # 早期 Graph 返回的 AddableValuesDict 只是一个对 dict 进行简单封装，重写了 __add__ 方法的dict, key 和 state 里定义的完全一样
    print(f"res.keys: {res.keys()}")  # dict_keys(['messages', 'count'])，key 和 state 里定义的完全一样
    print(f"output state: {res}")

    # 批量调用: batch/abatch 方法
    inputs = [{"messages": [], "count": 0}, {"messages": ["Hi"], "count": 1}]
    res_batch = compile_graph.batch(inputs=inputs)
    # print(f"{type(res_batch)}, {len(res_batch)}, {type(res_batch[0])}")
    # <class 'list'>, 2, <class 'langgraph.pregel.io.AddableValuesDict'>
    # batch 调用时，返回的是 List[AddableValuesDict]
    for item in res_batch:
        print(f"final state: {item}")


# %%
def message_graph_usage():
    """
    对于LLM场景，LangGraph 还提供了 MessageState 和 MessageGraph，方便直接使用。
    - MessageGraph 也有一个存放了 List[BaseMessage]的状态，但是似乎是匿名的，不能指定key。
    - MessagesState 就是一个 TypedDict，含有一个 messages 的key，存放了 List[BaseMessage]，并使用Annotated标注使用了 add_message()

     add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]
     整体的核⼼逻辑是合并两个消息列表，按 ID 更新现有消息。
     默认情况下，状态为“仅附加”，当新消息与现有消息具有相同的 ID时，进⾏更新。
     合并逻辑则是：如果right的消息与left的消息具有相同的 ID，则right的消息将替换left的消息，否则作为⼀条新的消息进⾏追加。
     返回值是合并后的 List[BaseMessage]。
    """
    def some_node(state: MessagesState):
        print("--> some_node start...")
        print(f"  state: {state}")
        print("<-- some_node end...")
        # 不能返回 dict，只能返回 List[BaseMessage]
        # return {'messages': [HumanMessage(content="some-node")]}
        return [HumanMessage(content="some-node")]

    graph = MessageGraph()
    graph.add_node(node="some_node", action=some_node)
    graph.set_entry_point("some_node")
    graph.set_finish_point("some_node")
    compile_graph = graph.compile(name='MessageGraph')

    # 同样，input_msg 也不能是 dict，而是 List[BaseMessage]
    # input_msg = {"messages": [HumanMessage(content="Hello World!")]}
    input_msg = [HumanMessage(content="Hello World!")]
    res = compile_graph.invoke(input=input_msg)
    print(res)


# %% ======================= 基于条件动态执行有状态图 =======================
def graph_conditional_usage():
    """
    展示有条件动态执行的状态图.
    主要是 Graph.add_conditional_edges() 方法的使用，该方法参数如下：
    - source: str, 指定 source 节点
    - path: 一个Python Callable 对象
      - 接受的参数是当前图的状态state
      - 在没有下面的 path_map 情况下，返回值会被作为 下一个/多个 执行Node的名称，多个Node会被并行执行
      - 如果配置的 path_map，则返回值会被作为 path_map 的key，映射到具体的下一个Node名称
    - path_map: dict[Hashable, str] | list[str]，对 path 的返回值进行映射处理
      - 以 dict 形式给出时，会将 path 的返回值作为 key，获取实际待执行的下一个 Node 名称
      - 以 list[str] 形式给出时，则表示后续执行的Node名称。实际上在 BranchSpec.from_path() 方法里会被转换成 {item: item} 的恒等映射dict
    """
    class SimpleState(TypedDict):
        messages: List[str]
        count: int

    def greet_node(state: SimpleState) -> SimpleState:
        state["messages"].append("Hello")
        state["count"] += 1
        print(f"--> greet_node running...")
        return state

    def reset_count_node(state: SimpleState):
        state["messages"].append("Reset Count")
        state["count"] = 0
        print(f"--> reset_count_node running...")
        return state

    def conditional_edge_check(state: SimpleState):
        print(f"==> conditional_edge_check running...")
        if state["count"] > 3:
            print(f"  Switch to -> reset_count_node")
            return "reset_count_node"
        else:
            print(f"  Switch to -> END")
            return END

    graph = StateGraph(state_schema=SimpleState)
    graph.add_node(node="greet_node", action=greet_node)
    graph.add_node(node="reset_count_node", action=reset_count_node)

    graph.set_entry_point("greet_node")
    # 根据state当前值选择下一个执行Node
    graph.add_conditional_edges(source="greet_node", path=conditional_edge_check)

    compile_graph: CompiledStateGraph = graph.compile(name='StateGraphWithConditionalEdges')

    res1 = compile_graph.invoke(input={"messages": [], "count": 0})
    print(res1)
    print("---------------------------------------")
    res2 = compile_graph.invoke(input={"messages": [], "count": 3})
    print(res2)


# %% ======================= Graph Checkpoint（短期记忆） 使用 =======================
def graph_checkpoint_usage():
    """
    checkpoint 机制是 LangGraph 提供的短期记忆机制。

    这里的短期记忆机制有两点含义：
    - 区分不同会话的历史对话记录，这个通过 LangGraph引入的 thread_id 来区分不同的会话。
    - 保存当前会话的历史对话记录（不仅是本次对话历史，还有之前的对话历史）

    为了展示 checkpoint 的效果，定义的 state 对象里，每个属性需要有一个 reducer 函数，这里使用了两种：
    1. 自定义 reducer
    2. LangGraph提供的 add_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage] 函数
    reducer 函数是为了保存/合并 本次对话历史，但它不能保存之前的对话历史。
    """
    def num_reducer(prev_num: List[int], curr_num: List[int]) -> List[int]:
        return prev_num + curr_num

    class ReduceState(TypedDict):
        messages: Annotated[List[BaseMessage], add_messages]
        num: Annotated[List[int], num_reducer]

    def greet_node(state: ReduceState) -> Dict[str, List[str]]:
        """
        此Node负责更新 ReduceState 里的 messages。
        """
        print(f"--> greet_node start...")
        print(f"  state: {state}")
        if len(state['messages']) > 0:
            # 获取状态里 messages 列表的最后一条消息（如果有）的内容
            # state_msg = state['messages'][-1]
            state_msg = state['messages'][-1].content
        else:
            # message没有消息，则默认为 Hello
            # 这里可以直接返回 str，不需要封装成 BaseMessage，因为 add_messages 函数会自动将 str 转换成 BaseMessage
            state_msg = 'Hello'
        if len(state["num"]) > 0:
            # 获取状态里的 num 列表的最后一个数字（如果有）
            state_num = state['num'][-1] + 1
        else:
            # num 列表为空，则默认为 0
            state_num = 0
        # 基于状态里最后信息，生成 message 列表里的新消息
        new_message = f"{state_msg}[{state_num}]"
        print(f"<-- greet_node end.")
        return {'messages': [new_message]}

    def increment_node(state: ReduceState) -> Dict[str, List[int]]:
        """
        此Node负责更新 ReduceState 里的 num。
        """
        print(f"--> increment_node start...")
        print(f"  state: {state}")
        if len(state["num"]) > 0:
            # 获取状态里 num 列表的最后一个数字（如果有），并递增
            state_num = state['num'][-1] + 1
        else:
            # state 里 num 列表为空，则默认为 0
            state_num = 0
        print(f"<-- increment_node end.")
        return {'num': [state_num]}

    graph = StateGraph(state_schema=ReduceState)
    graph.add_node(node="greet_node", action=greet_node)
    graph.add_node(node="increment_node", action=increment_node)
    graph.set_entry_point("greet_node")
    graph.add_edge("greet_node", "increment_node")
    graph.set_finish_point("increment_node")

    # 这个就是 checkpoint 对象，在compile的时候传入
    memory = MemorySaver()  # 基于内存的checkpoint简单实现
    compile_graph: CompiledStateGraph = graph.compile(name='StateGraphWithCheckpoint', checkpointer=memory)

    print("-------- user-1 call-1 ------------")
    # 调用的时候传入一个config字段，key 必须是 configurable，里面设置一个 thread_id，用于表示当前用户身份
    u1_config = {"configurable": {"thread_id": "user-1"}}

    u1_input_1 = {"messages": [], "num": []}
    print(f"u1_input_1: {u1_input_1}")
    u1_r1 = compile_graph.invoke(input=u1_input_1, config=u1_config)
    # print(type(u1_r1))  # <class 'langgraph.pregel.io.AddableValuesDict'>
    # print(f"u1_r1 state: {u1_r1}")
    print(f"==> u1_r1 state:")
    for msg, num in zip(u1_r1["messages"], u1_r1["num"]):
        # msg.pretty_print()
        print(f"  message: {msg.content}")
        print(f"  num: {num}")
        print("  ------")

    # 获取当前的状态，必须要使用 invoke 时同样的 config
    u1_r1_state: StateSnapshot = compile_graph.get_state(config=u1_config)
    # print(type(u1_r1_state))  # <class 'langgraph.types.StateSnapshot'>
    # print(u1_r1_state)
    print("\n==> u1_r1_state show:")
    print('  u1_r1_state.config: ', u1_r1_state.config)
    print('  u1_r1_state.metadata: ', u1_r1_state.metadata)
    # 下面就是当前 state 对象的值，应该和 u1_r1 的内容是一样的
    print('  type(u1_r1_state.values): ', type(u1_r1_state.values))  # <class 'dict'>
    print('  u1_r1_state.values: ', u1_r1_state.values)

    # ---- 获取历史状态，这也是 TimeTravel 的原理，获取历史状态，然后Replay ----
    print("\n-------- History State After User-1-Call-1 ------------")
    history_states: Iterator[StateSnapshot] = compile_graph.get_state_history(u1_config)
    # 下面展示的state顺序是 逆序的 ---------- KEY
    for index, state in enumerate(history_states, start=1):
        # print(type(state))  # <class 'langgraph.types.StateSnapshot'>
        # print(state)
        print(f"==> [{index}] state show:")
        print('  state.metadata: ', state.metadata)  # 这个有用，注意其中的 step 字段
        print('  state.values:   ', state.values)    # 这个有用，内容就是 StateSchema 定义的内容
        # print('  state.config: ', state.config)
        # print('  state.tasks: ', state.tasks)
        # print('  state.next: ', state.next)
        # print('  state.parent_config: ', state.parent_config)
        print("  ------")

    print("\n-------- user-1 call-2 ------------")
    u1_input_2 = {"messages": ["Call-2"], "num": [10]}
    print(f"u1_input_2: {u1_input_2}")
    u1_r2 = compile_graph.invoke(input=u1_input_2, config=u1_config)
    # print(f"u1_r2 state: {u1_r2}")
    print("==> u1_r2 state:")
    for msg, num in zip(u1_r2["messages"], u1_r2["num"]):
        # msg.pretty_print()
        print(f"  message: {msg.content}")
        print(f"  num: {num}")
        print("  ------")
    u1_r2_state = compile_graph.get_state(config=u1_config)
    print("\n==> u1_r2_state show:")
    # print('  u1_r2_state.config: ', u1_r2_state.config)
    # print('  u1_r2_state.metadata: ', u1_r2_state.metadata)
    print('  u1_r2_state.values: ', u1_r2_state.values)

    # ---- 获取第2次调用后的历史状态，状态是追加的 ----
    print("\n-------- History State After User-1-Call-2 ------------")
    history_states: Iterator[StateSnapshot] = compile_graph.get_state_history(u1_config)
    for index, state in enumerate(history_states, start=1):
        # print(type(state))  # <class 'langgraph.types.StateSnapshot'>
        # print(state)
        print(f"==> [{index}] state show:")
        print('  state.metadata: ', state.metadata)
        print('  state.values:   ', state.values)
        # print('  state.config: ', state.config)
        # print('  state.tasks: ', state.tasks)
        # print('  state.next: ', state.next)
        # print('  state.parent_config: ', state.parent_config)

    # ---- 从 Memory 对象里获取所有 checkpoint 列表 ----
    print("\n-------- Checkpoints ------------")
    checkpoint_iter: Iterator[CheckpointTuple] = memory.list(config=u1_config)
    # 下面展示的checkpoint顺序是 逆序的 ---------- KEY
    for index, checkpoint in enumerate(checkpoint_iter, start=1):
        # print(type(checkpoint))   # <class 'langgraph.checkpoint.base.CheckpointTuple'>
        # print(checkpoint)
        print(f"==> [{index}] checkpoint show:")
        # print('  checkpoint.parent_config: ', checkpoint.parent_config)
        print('  checkpoint.config:   ', checkpoint.config)
        print('  checkpoint.metadata: ', checkpoint.metadata)  # 这个信息有用，注意其中的 step 字段
        print('  checkpoint.checkpoint: ', checkpoint.checkpoint)  # 检查点内容类型是 Checkpoint 对象
        print('    checkpoint.checkpoint[id]: ', checkpoint.checkpoint['id'])
        print('    checkpoint.checkpoint[ts]: ', checkpoint.checkpoint['ts'])
        print('    checkpoint.checkpoint[updated_channels]: ', checkpoint.checkpoint['updated_channels'])
        print('    checkpoint.checkpoint[channel_values]: ', checkpoint.checkpoint['channel_values'])
        print('    checkpoint.checkpoint[channel_versions]: ', checkpoint.checkpoint['channel_versions'])
        # print('  checkpoint.pending_writes: ', checkpoint.pending_writes)


# %% ======================= Graph Store（长期记忆） 使用 =======================
def graph_store_usage():
    """
    LangGraph 的长期记忆是用于跨用户（thread_id）存储的。
    LangGraph的长期记忆存储的抽象基类是 langgraph.store.base.BaseStore。
    它采用 namespace + key + value 的层次来组织存储：
    - namespace: 支持多层次命名空间，使用 Tuple[str,...]来表示，比如 (user_id, application_name)
    - key: 对应命名空间下存储的 key
    - value: JSON结构，以dict形式存储
    """
    memory_store = InMemoryStore()
    memory_store.put(
        namespace=("user-1", "web"),
        key="web-k-1",
        value={"some": "some-value"}
    )
    memory_store.put(
        namespace=("user-1", "db"),
        key="db-k-1",
        value={"some": "some-value"}
    )
    print("==> list namespaces: ")
    # print(memory_store.list_namespaces())
    for namespace in memory_store.list_namespaces():
        print(f"  namespace: {namespace}")
        print("  ---")

    print("==> get item: ")
    print(memory_store.get(namespace=("user-1", "web"),  key="web-k-1"))
    print("----------------------------\n")

    def some_node(state: MessagesState, config: RunnableConfig, store: BaseStore) -> Dict[str, List[BaseMessage]]:
        """
        此Node中通过 RunnableConfig 类型拿到了运行时的配置，BaseStore 类型提示拿到了 store 配置。
        此外，langgraph 还提供了 get_store() 函数用于获取 store 配置。
        """
        print("--> some_node start...")
        print(f"  state: {state}")
        # 可以从 config 对象中获取 invoke 里传入的 config 参数信息，比如其中的 user_id 的内容，之后再查询用户相关的信息
        # print(f"  config: {config}")
        print(f"  use_id: {config.get('configurable', {}).get('user_id', '')}")
        # 在节点内部，可以通过 store = get_store() 来获取 store 对象  ----------- KEY
        store = get_store()
        store_namespaces = []
        for item in store.list_namespaces():
            store_namespaces.append('.'.join(item))
        store_namespaces = ';'.join(store_namespaces)
        print(f"  store-namespaces: {store_namespaces}")
        print("<-- some_node end...")
        return {'messages': [HumanMessage(content=store_namespaces)]}

    graph = StateGraph(MessagesState)
    graph.add_node(node="some_node", action=some_node)
    graph.set_entry_point("some_node")
    graph.set_finish_point("some_node")
    compile_graph = graph.compile(name='GraphWithStore', store=memory_store)

    # input_msg = {"messages": [{"role": "user", "content": "请列出当前Store的namespace"}]}
    input_msg = {"messages": [HumanMessage(content="请列出当前Store的namespace")]}
    config = {"configurable": {"user_id": "user-1"}}
    res = compile_graph.invoke(input=input_msg, config=config)
    # print(res)
    print("==> res:")
    for msg in res['messages']:
        # msg.pretty_print()
        print('  msg.content:', msg.content)
        print('  ---')


# %% ======================= Interrupt/Command (HIL) 机制 =======================
# 个人感觉 LangGraph 的HIL机制设计的不是很好用。
# 因为HIL触发时，会从 graph.invoke() 返回，此时需要用户在这里对返回的内容进行判断是否包含 Interrupt 信息：
# - 如果包含，则进行 HIL 干预后，再次调用 graph.invoke() 恢复执行
# - 如果不包含，那么拿到的就是本次输入的最终结果
# 也就是说，本来是单次调用 invoke() 的流程，现在不得不使用一个 while 循环来处理 invoke() 的 interrupt 流程；
# 更麻烦的是，如果有多个节点会触发 HIL，那还需要在这个 while 循环里增加一个 if 或者 switch 判断，处理多个 HIL 的情况。
def graph_dynamic_interrupt_usage():
    """
    展示 LangGraph 的 Human-Interrupt 使用 —— 动态断点设置。
    通过 interrupt() 函数 + Command 对象 实现断点触发及恢复。

    这种方式可以在 node 内执行一些断点处理逻辑。
    实际上，查看 interrupt() 的源码可以发现，它其实是抛出一个 GraphInterrupt 异常来实现中断Graph执行的。

    注意，使用 interrupt() 在 node 内动态设置断点，后续使用 Command 对象恢复执行时，
    **整个 node 内的代码都会被重新执行一次！！！**
    而不是从 interrupt() 函数的部分恢复执行（类似 yield 的效果）。
    """
    def num_reducer(prev_num: List[int], curr_num: List[int]) -> List[int]:
        return prev_num + curr_num

    class HumanInterruptState(TypedDict):
        num: Annotated[List[int], num_reducer]
        human_msg: str

    def greet_node(state: HumanInterruptState) -> Dict[str, str]:
        print(f"--> greet_node start...")
        if len(state["num"]) > 0:
            value = {"state.num": state['num']}
        else:
            value = {"state.num": 0}
        # --------------------------------------------------------------------------
        print(f"  ==> greet_node is waiting for human response with value: {value}")
        # 使用 interrupt 函数打断图的执行，等待人工输入 --------------- KEY
        # interrupt() 函数的参数 value 会被返回
        human_response = interrupt(value=value)
        # interrupt() 函数的返回值就是断点恢复执行时通过 Command 对象的 resume 参数设置的值 --------- KEY
        print(f"  <== greet_node received human interrupt response: {human_response}")
        # 但是有一点需要特别注意：断点恢复执行时，整个 greet_node 里的逻辑都会被重新执行，
        # 而不是从 interrupt() 函数返回后的部分继续执行（类似于 yield 的效果）
        # --------------------------------------------------------------------------
        print(f"<-- greet_node end.")
        return {'human_msg': human_response["human_msg"]}

    def increment_node(state: HumanInterruptState) -> Dict[str, List[int]]:
        print(f"--> increment_node start...")
        if len(state["num"]) > 0:
            state_num = state['num'][-1] + 1
        else:
            state_num = 0
        print(f"<-- increment_node end.")
        return {'num': [state_num]}

    graph = StateGraph(state_schema=HumanInterruptState)
    graph.add_node(node="greet_node", action=greet_node)
    graph.add_node(node="increment_node", action=increment_node)
    graph.set_entry_point("greet_node")
    graph.add_edge("greet_node", "increment_node")
    graph.set_finish_point("increment_node")

    # HIL 需要借助 checkpointer 才能使用
    memory = MemorySaver()
    compile_graph: CompiledStateGraph = graph.compile(name='StateGraphWithDynamicHIL', checkpointer=memory)

    u1_config = {"configurable": {"thread_id": "user-1"}}
    u1_input = {"messages": '', "num": []}
    print(f"u1_input = {u1_input}")
    u1_r1 = compile_graph.invoke(input=u1_input, config=u1_config)
    print(f"u1_r1 state: {u1_r1}")
    # 通过 interrupt() 函数触发 Human-Interrupt 时，value 参数可以通过 __interrupt__ 这个key获取
    print(f"__interrupt__: {u1_r1['__interrupt__']}")
    print("--------------------")
    resume = {'human_msg': "hello world"}
    print(f"resume: {resume}")
    # 断点恢复时，通过 Command 对象传入的 resume 参数的值，会被作为 interrupt() 函数的返回值
    u1_r1_command = Command(resume=resume)
    u1_r1_continue = compile_graph.invoke(input=u1_r1_command, config=u1_config)
    print(f"u1_r1_continue: {u1_r1_continue}")


# %%
def graph_fixed_breakpoint_usage():
    """
    展示 LangGraph 的 Human-Interrupt 使用 —— 固定断点设置。
    在 Graph.compile() 方法里通过 interrupt_before 参数，指定在某些 node 前/后 设置断点。
    这种方式把断点时的处理逻辑放到了 Graph 外面。
    """
    class HumanInterruptState(TypedDict):
        msg: Annotated[BaseMessage, add_messages]

    def greet_node(state: HumanInterruptState) -> Dict[str, str]:
        print(f"--> greet_node start...")
        print(f"  state: {state}")
        print(f"<-- greet_node end.")
        return {'msg': "Hello LangGraph"}

    def show_node(state: HumanInterruptState) -> Dict[str, str]:
        print(f"--> show_node start...")
        print(f"  state: {state}")
        print(f"<-- show_node end.")
        return {'msg': "I'm LangGraph"}

    graph = StateGraph(state_schema=HumanInterruptState)
    graph.add_node(node="greet_node", action=greet_node)
    graph.add_node(node="show_node", action=show_node)
    graph.set_entry_point("greet_node")
    graph.add_edge("greet_node", "show_node")
    graph.set_finish_point("show_node")

    # HIL 需要借助 checkpointer 才能使用
    memory = MemorySaver()
    compile_graph: CompiledStateGraph = graph.compile(
        name='StateGraphWithFixedHIL',
        checkpointer=memory,
        interrupt_before=["show_node"],  # 指定在某些节点前设置断点
        # interrupt_after=["greet_node"]    # 指定在某些节点后设置断点
    )

    u1_config = {"configurable": {"thread_id": "user-1"}}
    u1_input = {"msg": []}
    print(f"u1_input = {u1_input}")
    u1_r1 = compile_graph.invoke(input=u1_input, config=u1_config)
    # 控制台日志可以看到，只执行了 greet_node 节点，show_node 节点没有执行
    print(type(u1_r1))  # <class 'dict'>
    print(f"u1_r1 state: {u1_r1}")
    # {'msg': [HumanMessage(content='Hello LangGraph', additional_kwargs={}, response_metadata={}, id='7685ea03-46b0-467c-9c5c-eab8ad627935')]}
    # -------------------------
    # 在断点停住之后，可以使用 graph.get_state() 方法获取当前的状态；使用 graph.update_state() 方法来修改状态
    u1_r1_state: StateSnapshot = compile_graph.get_state(config=u1_config)
    print(u1_r1_state.values)
    # 修改状态
    conf: RunnableConfig = compile_graph.update_state(config=u1_config, values={'msg': 'Hello LangGraph from HIL'})
    # u1_r1_state.values['msg'] = [HumanMessage(content='Hello LangGraph from HIL')]
    # compile_graph.update_state(config=u1_config, values=u1_r1_state)
    print(conf)
    # 检查修改的状态
    s = compile_graph.get_state(config=u1_config)
    print(s.values)
    # -------------------------
    # 恢复执行，input输入 None，
    # 这里恢复时，会从上次中断点继续执行，即从 show_node 节点开始执行，而不会再次执行 greet_node 节点
    u1_r1_continue = compile_graph.invoke(input=None, config=u1_config)
    print(f"u1_r1_continue: {u1_r1_continue}")


# %% ======================= 结合 LangChain 的 ChatBot 案例 =======================
def chatbot_example():
    class MsgState(TypedDict):
        messages: Annotated[list[Union[str, BaseMessage]], add_messages]

    graph = StateGraph(MsgState)

    client_chat = get_client_chat()
    # res = client_chat.invoke(input=[{'role': 'user', 'content': '你好，可以和我聊聊历史吗？'}])
    # print(res.content)
    def chatbot_node(state: MsgState):
        print(f"--> chatbot_node start...")
        print(f"  state: {state}")
        response = client_chat.invoke(input=state["messages"])
        print(f"<-- chatbot_node end.")
        return {"messages": [response]}

    graph.add_node(node='chatbot', action=chatbot_node)
    graph.set_entry_point('chatbot')
    graph.set_finish_point('chatbot')

    memory = MemorySaver()
    compile_graph = graph.compile(name='ChatBotGraph', checkpointer=memory)

    u1_config = {"configurable": {"thread_id": "user-1"}}
    print("-------- user-1 chat-round-1 ------------")
    msg_1 = [{'role': 'user', 'content': '你好，可以和我聊聊历史吗？'}]
    u1_r1 = compile_graph.invoke(input={"messages": msg_1}, config=u1_config)
    # print(type(u1_r1))  # <class 'langgraph.pregel.io.AddableValuesDict'>
    # print(u1_r1['messages'])
    for msg in u1_r1['messages']:
        # print(msg.content)
        msg.pretty_print()
    u1_r1_state = compile_graph.get_state(config=u1_config)
    # print("\n---> u1_r1_state show:")
    # print('  u1_r1_state.config: ', u1_r1_state.config)
    # print('  u1_r1_state.metadata: ', u1_r1_state.metadata)
    # print('  u1_r1_state.values: ', u1_r1_state.values)
    print('\nu1_r1_state.values -> messages:')
    for index, message in enumerate(u1_r1_state.values['messages'], start=1):
        print(f"[{index}] {message.content}")

    print("\n-------- user-1 chat-round-2 ------------")
    msg_2 = [{'role': 'user', 'content': '我们刚才聊了什么？'}]
    u1_r2 = compile_graph.invoke(input={"messages": msg_2}, config=u1_config)
    # print(u1_r2)
    for msg in u1_r2['messages']:
        # print(msg.content)
        msg.pretty_print()
    u1_r2_state = compile_graph.get_state(config=u1_config)
    # print("\n---> u1_r2_state show:")
    # print('  u1_r2_state.config: ', u1_r2_state.config)
    # print('  u1_r2_state.metadata: ', u1_r2_state.metadata)
    # print('  u1_r2_state.values: ', u1_r2_state.values)
    print('\nu1_r1_state.values -> messages:')
    for index, message in enumerate(u1_r2_state.values['messages'], start=1):
        print(f"[{index}] {message.content}")


# %% ======================= Tool调用 =======================
def chatbot_tool_usage_manual():
    """
    展示tool调用，这里先手动实现 tool 调用.
    """
    # 定义 tool
    @tool(description="使用龙球(DragonBall)算法计算两个数字的结果")
    def dragon_ball_algorithm_tool(x: Annotated[int, "第一个数字"], y: Annotated[int, "第二个数字"]) -> int:
        return x + y + 1

    # 初始化 ChatLLM，并绑定 tool
    client_chat = get_client_chat()
    client_chat_tool = client_chat.bind_tools(tools=[dragon_ball_algorithm_tool])

    # 定义 StateGraph
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    #  定义 chatbot 节点
    def chatbot_node(state: State):
        print(f"--> chatbot_node start...")
        print(f"  state: {state}")
        response = client_chat_tool.invoke(input=state["messages"])
        print(f"<-- chatbot_node end.")
        return {"messages": [response]}

    # 定义一个 Tools 调用节点
    class CustomToolNode:
        """
        A node that runs the tools requested in the last AIMessage.
        此示例来自官方文档 [Create a function to run the tools](https://langchain-ai.github.io/langgraph/tutorials/get-started/2-add-tools/#5-create-a-function-to-run-the-tools)
        """
        def __init__(self, tools: List[BaseTool]) -> None:
            # 使用dict，存储多个工具，将工具名称映射到工具对象
            self.tools_by_name = {t.name: t for t in tools}

        def __call__(self, inputs: State):
            # 尝试从 state 中获取最后一个元素
            if messages := inputs.get("messages", []):
                message = messages[-1]
            else:
                raise ValueError("No message found in input")
            # 触发 tool 调用时，最后一个 message 应该是 AIMessage，并且有 tool_calls 属性 —— 不过这个判断不放在这里，而是放在了 conditional_edge 中
            assert isinstance(message, AIMessage), "Last message is not an AIMessage"
            outputs = []
            for tool_call in message.tool_calls:
                tool_func = self.tools_by_name[tool_call["name"]]
                tool_result = tool_func.invoke(tool_call["args"])
                outputs.append(
                    ToolMessage(
                        content=json.dumps(tool_result),
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )
            return {"messages": outputs}

    # 定义判断是否调用 tool 节点的 条件边
    def route_tools(state: State):
        """
        Use in the conditional_edge to route to the ToolNode if the last message has tool calls. Otherwise, route to the end.
        """
        if isinstance(state, list):
            ai_message = state[-1]
        elif messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")
        assert isinstance(ai_message, AIMessage), "Last message is not an AIMessage"
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
        return END

    # 构建图
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", CustomToolNode(tools=[dragon_ball_algorithm_tool]))
    graph_builder.add_conditional_edges("chatbot", route_tools)
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")
    graph = graph_builder.compile(name="ChatbotWithToolGraph")

    # 调用
    input_msgs = [
        SystemMessage(content='你是一个算术专家'),
        HumanMessage(content='请使用龙球(DragonBall)算法计算一下 2019 和 2022 的结果'),
    ]
    res = graph.invoke(input={"messages": input_msgs})
    for msg in res['messages']:
        msg.pretty_print()

# %%
def chatbot_tool_usage_prebuilt():
    """
    还是上面的例子，不过这次使用 LangGraph 提供预构建的 ToolNode 和 tools_condition
    """
    # 定义 tool
    @tool(description="使用龙球(DragonBall)算法计算两个数字的结果")
    def dragon_ball_algorithm_tool(x: Annotated[int, "第一个数字"], y: Annotated[int, "第二个数字"]) -> int:
        return x + y + 1

    # ------ 工具上下文使用 ------
    # 使用 dataclass 自定义一个上下文，里面包含需要使用的字段信息
    @dataclass
    class Context:
        user_id: str

    @tool(description="获取工具上下文")
    def get_tool_context(runtime: ToolRuntime[Context]) -> str:
        # 从工具运行时获取工具上下文里的字段
        user_id = runtime.context.user_id
        preferences: str = "The user prefers you to write a brief and polite email."
        if runtime.store:
            if memory := runtime.store.get(("users",), user_id):
                preferences = memory.value["preferences"]
        return preferences
    # ------ 工具上下文使用 ------

    # 初始化 ChatLLM，并绑定 tool
    client_chat = get_client_chat()
    client_chat_tool = client_chat.bind_tools(tools=[dragon_ball_algorithm_tool])

    # 定义 StateGraph
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    #  定义 chatbot 节点
    def chatbot_node(state: State):
        print(f"--> chatbot_node start...")
        print(f"  state: {state}")
        response = client_chat_tool.invoke(input=state["messages"])
        print(f"<-- chatbot_node end.")
        return {"messages": [response]}

    # 定义 tools 调用节点，直接使用 LangGraph 提供的 ToolNode 类 —— 这个类内部的实现就类似于上面的 CustomToolNode
    tool_node = ToolNode(tools=[dragon_ball_algorithm_tool])

    # 构建图
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", tool_node)
    # 判断是否调用 tool 节点的 条件边 直接使用 tools_condition # TODO 这个条件判断逻辑有待仔细研究
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")
    graph = graph_builder.compile(name="ChatbotWithToolGraph")

    # 调用
    input_msgs = [
        SystemMessage(content='你是一个算术专家'),
        HumanMessage(content='请使用龙球(DragonBall)算法计算一下 2019 和 2022 的结果'),
    ]
    res = graph.invoke(input={"messages": input_msgs})
    for msg in res['messages']:
        msg.pretty_print()


# %% ======================= ReAct Agent 生成 =======================
def react_agent_usage():
    """
    API文档: [create_react_agent](https://langchain-ai.github.io/langgraph/reference/agents/#langgraph.prebuilt.chat_agent_executor.create_react_agent)
    注意：create_react_agent() 这个API 在 LangGraph v1.0 版本被标记为了废弃，后续推荐直接使用 langchain.agents 里提供的 create_agent()
    """
    @tool(description="使用龙球(DragonBall)算法计算两个数字的结果")
    def dragon_ball_algorithm(x: Annotated[int, "第一个数字"], y: Annotated[int, "第二个数字"]) -> int:
        return x + y + 1

    @tool(description="检查龙球(DragonBall)算法的结果是否正确")
    def dragon_ball_check(x: Annotated[int, "第一个数字"], y: Annotated[int, "第二个数字"], z: Annotated[int, "结果数字"]) -> int:
        return x + y + 1 == z

    tools = [dragon_ball_algorithm, dragon_ball_check]
    # 可以试下不传入检查结果的工具，模型会给出不一样的回答
    # tools = [dragon_ball_algorithm]

    tool_node = ToolNode(tools=tools)
    client_chat = get_client_chat()
    client_chat_tool = client_chat.bind_tools(tools=tools)
    memory = MemorySaver()

    # 创建 Agent 的图，这里使用默认的 AgentState，当然也可以自定义
    # tools 参数可以使用 ToolNode，也可以直接使用 List[Tool]
    agent = create_react_agent(name='ReAct-Agent', model=client_chat_tool, tools=tool_node, checkpointer=memory)
    print(type(agent))
    print(agent.name)

    # 输入
    input_msgs = [
        SystemMessage(content='你是一个算术专家'),
        HumanMessage(content='请使用龙球(DragonBall)算法计算一下 2019 和 2022 的结果，并检查算法的结果是否正确'),
    ]
    config = {"configurable": {"thread_id": "1"}}

    # 调用
    res = agent.invoke(input={"messages": input_msgs}, config=config)
    print(f"type(res): {type(res)}")    # <class 'langgraph.pregel.io.AddableValuesDict'>
    print(res.keys())    # dict_keys(['messages'])
    print(res)
    print("-------------------------------")
    for msg in res['messages']:
        msg.pretty_print()


# %% ======================= Graph Fault Tolerance =======================
def graph_fault_tolerance_timeout_usage() -> None:
    """
    展示 Graph Node 执行超时时的容错处理。

    LangGraph 提供两种超时机制：
    1. run_timeout: 硬性墙上时钟上限，单次尝试的总时长限制，不会被任何进度信号重置
    2. idle_timeout: 进度重置上限，当节点停止产生可观察的进度信号达到指定时长时触发

    两者可以组合使用，哪个先触发就取消当前尝试。
    超时后会抛出 NodeTimeoutError，该异常默认是可重试的（在 default_retry_on 范围内）。
    
    idle_time的刷新方式可以通过 TimeoutPolicy 的 refresh_on 参数指定，有如下取值：
    - auto：默认值，当节点有任何进度行为（比如stream返回、更新状态、回调函数执行等），都会刷新 idle_timeout 时钟。
    - heartbeat：只有当用户在节点内部调用 Runtime.heartbeat() 时，才会刷新 idle_timeout 时钟。

    注意：timeout 仅支持 async 节点，同步节点设置 timeout 会在 compile 时报错。
    """
    # ---- 1. run_timeout 示例：硬性时间上限 ----
    class TimeoutState(TypedDict):
        result: str
        attempts: Annotated[List[int], lambda prev, curr: prev + curr]

    async def slow_node(state: TimeoutState, runtime: Runtime) -> Dict[str, str]:
        """模拟一个耗时过长的节点"""
        print(f"  [slow_node] attempt #{runtime.execution_info.node_attempt} start, sleeping 3s...")
        await asyncio.sleep(3)  # 模拟耗时操作，超过了 run_timeout=1
        print(f"  [slow_node] finished (should not reach here)")
        return {"result": "done"}

    async def fast_node(state: TimeoutState) -> Dict[str, str]:
        """正常速度的节点"""
        print(f"  [fast_node] running...")
        return {"result": "fast-done"}

    graph = StateGraph(TimeoutState)
    graph.add_node(
        "slow_node", slow_node,
        timeout=TimeoutPolicy(run_timeout=1),      # 1秒超时
        retry_policy=RetryPolicy(max_attempts=2),  # 最多尝试2次（含首次）
    )
    graph.add_node("fast_node", fast_node)
    graph.add_edge(START, "slow_node")
    graph.add_edge("slow_node", "fast_node")
    graph.add_edge("fast_node", END)
    compile_graph = graph.compile(name='TimeoutGraph')

    print("==> run_timeout 示例：slow_node 设置 run_timeout=1s，但 sleep 3s")
    try:
        res = asyncio.run(compile_graph.ainvoke(input={"result": "", "attempts": []}))
        print(f"  result: {res}")
    except NodeTimeoutError as e:
        print(f"  NodeTimeoutError caught: node={e.node}, kind={e.kind}, elapsed={e.elapsed:.2f}s")
        print(f"  run_timeout={e.run_timeout}s, idle_timeout={e.idle_timeout}")

    # ---- 2. idle_timeout + heartbeat 示例 ----
    print("\n==> idle_timeout + heartbeat 示例")

    class IdleState(TypedDict):
        result: str

    async def long_running_with_heartbeat(state: IdleState, runtime: Runtime) -> Dict[str, str]:
        """模拟长时间运行但定期发送心跳的节点"""
        print(f"  [long_running] start, will run ~2s with heartbeats every 0.5s...")
        for i in range(4):
            await asyncio.sleep(0.5)
            runtime.heartbeat()  # 手动重置 idle 时钟 -------- KEY
            print(f"    heartbeat #{i+1} sent")
        print(f"  [long_running] finished")
        return {"result": "completed-with-heartbeats"}

    graph2 = StateGraph(IdleState)
    graph2.add_node(
        "long_running", long_running_with_heartbeat,
        timeout=TimeoutPolicy(idle_timeout=1, refresh_on="heartbeat"),  # idle_timeout=1s，仅 heartbeat 刷新
    )
    graph2.add_edge(START, "long_running")
    graph2.add_edge("long_running", END)
    compile_graph2 = graph2.compile(name='IdleTimeoutGraph')

    res2 = asyncio.run(compile_graph2.ainvoke(input={"result": ""}))
    print(f"  result: {res2}")

    # ---- 3. timeout + retry 组合 ----
    print("\n==> timeout + retry 组合示例")

    class RetryTimeoutState(TypedDict):
        result: str
        attempts: Annotated[List[int], lambda prev, curr: prev + curr]

    async def flaky_node(state: RetryTimeoutState, runtime: Runtime) -> Dict[str, str]:
        """模拟一个偶尔超时的节点，通过 runtime 检查当前尝试次数"""
        attempt = runtime.execution_info.node_attempt
        print(f"  [flaky_node] attempt #{attempt}")
        if attempt < 3:
            print(f"    simulating timeout (sleep 2s, run_timeout=1s)...")
            await asyncio.sleep(2)
        print(f"    success on attempt #{attempt}!")
        return {"result": f"success-on-attempt-{attempt}", "attempts": [attempt]}

    graph3 = StateGraph(RetryTimeoutState)
    graph3.add_node(
        "flaky_node", flaky_node,
        timeout=TimeoutPolicy(run_timeout=1),
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.3, backoff_factor=1.5),
    )
    graph3.add_edge(START, "flaky_node")
    graph3.add_edge("flaky_node", END)
    compile_graph3 = graph3.compile(name='RetryTimeoutGraph')

    try:
        res3 = asyncio.run(compile_graph3.ainvoke(input={"result": "", "attempts": []}))
        print(f"  result: {res3}")
    except NodeTimeoutError as e:
        print(f"  All retries exhausted: {e}")


def graph_fault_tolerance_usage() -> None:
    """
    展示 Graph Node 执行抛出异常（包含超时异常）时的容错处理。

    LangGraph 提供三种可组合的容错机制：
    1. RetryPolicy: 根据异常类型和退避设置自动重试失败的尝试
    2. Timeouts: 针对超时异常的处理策略，见上面的 graph_fault_tolerance_timeout_usage() 示例
    3. error_handler: 在所有重试耗尽后运行的异常处理函数，用于恢复或更新状态并路由到其他节点
    
    这3种机制是递进式的：节点异常（包括超时异常） → retry_policy 判断是否重试 → 重试耗尽后 → error_handler 处理 。   
    
    上述3种方式可以在每个节点单独配置，使用Graph.add_node() 方法提供的 retry_policy / timeout / error_handler 参数。
    也可以使用 StateGraph.set_node_defaults()方法为所有节点统一配置默认的 retry_policy / timeout / error_handler。
    """
    # ---- 1. RetryPolicy 基本使用 + 自定义 retry_on ----
    print("==> 1. RetryPolicy 基本使用 + 自定义 retry_on")

    class RetryState(TypedDict):
        status: str
        call_count: Annotated[int, lambda prev, curr: prev + curr]

    # 自定义一个业务异常
    class TransientAPIError(Exception):
        """可重试的临时 API 错误"""
        pass

    class FatalConfigError(Exception):
        """不可重试的致命配置错误"""
        pass

    def custom_retry_on(exc: BaseException) -> bool:
        """自定义重试判断：只重试 TransientAPIError，其他异常不重试"""
        if isinstance(exc, TransientAPIError):
            return True
        if isinstance(exc, FatalConfigError):
            return False
        # 其他异常使用默认策略
        return default_retry_on(exc)

    call_counter = {"count": 0}

    def call_external_api(state: RetryState) -> Dict[str, str]:
        """模拟调用外部 API，前2次抛出可重试异常，第3次成功"""
        call_counter["count"] += 1
        cnt = call_counter["count"]
        print(f"  [call_external_api] call #{cnt}")
        if cnt < 3:
            print(f"    -> raising TransientAPIError (retryable)")
            raise TransientAPIError(f"API temporarily unavailable (attempt #{cnt})")
        print(f"    -> success!")
        return {"status": "api-ok", "call_count": cnt}

    graph = StateGraph(RetryState)
    graph.add_node(
        "call_external_api", call_external_api,
        retry_policy=RetryPolicy(
            max_attempts=4,
            initial_interval=0.2,
            backoff_factor=2.0,
            retry_on=custom_retry_on,
        ),
    )
    graph.add_edge(START, "call_external_api")
    graph.add_edge("call_external_api", END)
    compile_graph = graph.compile(name='RetryGraph')

    res = compile_graph.invoke(input={"status": "", "call_count": 0})
    print(f"  result: {res}")

    # ---- 2. error_handler + Command 路由（Saga 补偿模式） ----
    print("\n==> 2. error_handler + Command 路由（Saga 补偿模式）")

    class SagaState(TypedDict):
        status: str

    def reserve_inventory(state: SagaState) -> Dict[str, str]:
        """预留库存 —— 总是成功"""
        print(f"  [reserve_inventory] inventory reserved")
        return {"status": "reserved"}

    def charge_payment(state: SagaState) -> Dict[str, str]:
        """扣款 —— 模拟失败"""
        print(f"  [charge_payment] charging... FAILED!")
        raise RuntimeError("payment gateway timeout")

    def payment_error_handler(state: SagaState, error: NodeError) -> Command:
        """扣款失败后的补偿处理：释放库存并路由到最终节点"""
        print(f"  [payment_error_handler] compensating for node '{error.node}': {error.error}")
        return Command(
            update={"status": f"compensated: released inventory after {error.node} failure"},
            goto="finalize",
        )

    def finalize(state: SagaState) -> Dict[str, str]:
        """最终节点"""
        print(f"  [finalize] order finalized with status: {state['status']}")
        return state

    graph2 = StateGraph(SagaState)
    graph2.add_node("reserve_inventory", reserve_inventory)
    graph2.add_node(
        "charge_payment", charge_payment,
        retry_policy=RetryPolicy(max_attempts=2, retry_on=ConnectionError),  # 只重试 ConnectionError
        error_handler=payment_error_handler,  # 重试耗尽后执行补偿
    )
    graph2.add_node("finalize", finalize)
    graph2.add_edge(START, "reserve_inventory")
    graph2.add_edge("reserve_inventory", "charge_payment")
    # charge_payment 的 error_handler 通过 Command(goto="finalize") 路由到 finalize
    graph2.add_edge("finalize", END)
    compile_graph2 = graph2.compile(name='SagaGraph')

    res2 = compile_graph2.invoke(input={"status": ""})
    print(f"  result: {res2}")

    # ---- 3. set_node_defaults 统一默认配置 ----
    print("\n==> 3. set_node_defaults 统一默认配置")

    class DefaultState(TypedDict):
        status: str

    def default_error_handler(state: DefaultState, error: NodeError) -> Dict[str, str]:
        """全局默认错误处理器"""
        print(f"  [default_error_handler] recovered from '{error.node}': {error.error}")
        return {"status": f"recovered: {error.error}"}

    def step_a(state: DefaultState) -> Dict[str, str]:
        print(f"  [step_a] running...")
        return {"status": "step-a-ok"}

    def step_b(state: DefaultState) -> Dict[str, str]:
        print(f"  [step_b] running... FAILED!")
        raise ValueError("step_b something went wrong")

    def step_c(state: DefaultState) -> Dict[str, str]:
        print(f"  [step_c] running...")
        return {"status": "step-c-ok"}

    graph3 = (
        StateGraph(DefaultState)
        .set_node_defaults(
            retry_policy=RetryPolicy(max_attempts=2),
            error_handler=default_error_handler,
        )
        .add_node("step_a", step_a)
        .add_node("step_b", step_b)  # 使用默认的 error_handler
        .add_node("step_c", step_c)
        .add_edge(START, "step_a")
        .add_edge("step_a", "step_b")
        .add_edge("step_b", "step_c")
        .add_edge("step_c", END)
        .compile(name='DefaultsGraph')
    )

    res3 = graph3.invoke(input={"status": ""})
    print(f"  result: {res3}")

    # ---- 4. 不可重试异常直接触发 error_handler ----
    print("\n==> 4. 不可重试异常直接触发 error_handler")

    class ImmediateErrorState(TypedDict):
        status: str

    def node_with_fatal_error(state: ImmediateErrorState) -> Dict[str, str]:
        print(f"  [node_with_fatal_error] raising FatalConfigError...")
        raise FatalConfigError("invalid configuration: missing API key")

    def fatal_error_handler(state: ImmediateErrorState, error: NodeError) -> Command:
        print(f"  [fatal_error_handler] fatal error in '{error.node}': {error.error}")
        return Command(
            update={"status": f"aborted: {error.error}"},
            goto=END,
        )

    graph4 = StateGraph(ImmediateErrorState)
    graph4.add_node(
        "node_with_fatal_error", node_with_fatal_error,
        retry_policy=RetryPolicy(max_attempts=3, retry_on=custom_retry_on),
        error_handler=fatal_error_handler,
    )
    graph4.add_edge(START, "node_with_fatal_error")
    compile_graph4 = graph4.compile(name='FatalErrorGraph')

    res4 = compile_graph4.invoke(input={"status": ""})
    print(f"  result: {res4}")


# %% ======================= Graph Stream =======================
def graph_stream_usage_v1():
    """
    展示 LangGraph 的 Stream API V1 使用（默认版本）。
    LangGraph的 StateGraph 提供了 同步stream() 和 异步astream() 方法，用于配合LLM的流式输出。

    LangGraph v1.1+ 版本引入了新的统一Stream返回格式，可以通过 version="v2" 参数指定，不过目前还是默认使用 version="v1"。
    此示例主要基于 V1 版本，V2 版本参见下面的 graph_stream_usage_v2() 示例。

    V1 版本的输出格式特点：
    - 单个 stream_mode：直接返回原始数据（dict）
    - 多个 stream_mode：返回 (mode, data) 元组
    - 子图 (subgraphs=True)：返回 (namespace, data) 或 (namespace, mode, data) 元组

    Stream的模式可以使用 stream_mode 参数指定，支持的模式有：
    - updates: 每个步骤后流式传输状态的更新（增量）
    - values: 每个步骤后流式传输状态的完整值
    - messages: 流式传输 LLM 的 token 级别输出，返回 (message_chunk, metadata) 元组
    - custom: 自定义流，通过 get_stream_writer() 在节点内发送自定义数据
    - checkpoints: 流式传输 checkpoint 事件（需要 checkpointer）
    - tasks: 流式传输任务开始/完成事件（需要 checkpointer）
    - debug: 流式传输尽可能多的调试信息（结合 checkpoints + tasks + 额外元数据）
    """

    # ======================= 1. updates / values 模式（fake demo，不调用模型） =======================
    print("=" * 30 + " V1: updates / values 模式 " + "=" * 30)

    class SimpleState(TypedDict):
        topic: str
        result: str

    def refine_topic(state: SimpleState) -> Dict[str, str]:
        """模拟对 topic 进行加工"""
        return {"topic": state["topic"] + " and cats"}

    def generate_result(state: SimpleState) -> Dict[str, str]:
        """模拟生成结果"""
        return {"result": f"This is a result about {state['topic']}"}

    graph: CompiledStateGraph = (
        StateGraph(SimpleState)
        .add_node("refine_topic", refine_topic)
        .add_node("generate_result", generate_result)
        .add_edge(START, "refine_topic")
        .add_edge("refine_topic", "generate_result")
        .add_edge("generate_result", END)
        .compile()
    )

    # --- updates 模式：只返回每个节点对状态的更新（增量） ---
    print("\n--- updates 模式（增量更新） ---")
    input_updates = {"topic": "ice cream", "result": ""}
    print(f"  input: {input_updates}")
    for chunk in graph.stream(input_updates, stream_mode="updates"):
        # V1: 单模式直接返回 dict，key 为节点名，value 为该节点的更新
        print(f"  chunk: {chunk}")

    # --- values 模式：返回每个步骤后的完整状态 ---
    print("\n--- values 模式（完整状态） ---")
    input_values = {"topic": "ice cream", "result": ""}
    print(f"  input: {input_values}")
    for chunk in graph.stream(input_values, stream_mode="values"):
        # V1: 单模式直接返回完整 state dict
        print(f"  chunk: {chunk}")

    # ======================= 2. custom 模式（fake demo） =======================
    print("\n" + "=" * 30 + " V1: custom 模式 " + "=" * 30)

    class CustomState(TypedDict):
        query: str
        answer: str

    def custom_node(state: CustomState) -> Dict[str, str]:
        """在节点内通过 get_stream_writer() 发送自定义进度数据"""
        writer = get_stream_writer()
        writer({"progress": "step-1: thinking..."})
        writer({"progress": "step-2: generating..."})
        return {"answer": f"Answer to: {state['query']}"}

    graph_custom: CompiledStateGraph = (
        StateGraph(CustomState)
        .add_node("custom_node", custom_node)
        .add_edge(START, "custom_node")
        .add_edge("custom_node", END)
        .compile()
    )

    print("\n--- custom 模式 ---")
    input_custom = {"query": "hello", "answer": ""}
    print(f"  input: {input_custom}")
    for chunk in graph_custom.stream(input_custom, stream_mode="custom"):
        # V1: custom 模式直接返回 writer 发送的 dict
        print(f"  custom event: {chunk}")

    # ======================= 3. messages 模式（需要调用模型） =======================
    print("\n" + "=" * 30 + " V1: messages 模式 " + "=" * 30)

    class MsgState(TypedDict):
        topic: str
        joke: str

    client_chat: BaseChatModel = get_client_chat()

    def call_model(state: MsgState) -> Dict[str, str]:
        """调用 LLM 生成内容 —— messages 模式会捕获 token 级别的输出"""
        response: AIMessage = client_chat.invoke(
            [{"role": "user", "content": f"Generate a short joke about {state['topic']}"}]
        )
        return {"joke": response.content}

    graph_msg: CompiledStateGraph = (
        StateGraph(MsgState)
        .add_node("call_model", call_model)
        .add_edge(START, "call_model")
        .add_edge("call_model", END)
        .compile()
    )

    print("\n--- messages 模式（LLM token 级别流式输出） ---")
    input_msg = {"topic": "ice cream", "joke": ""}
    print(f"  input: {input_msg}")
    first_chunk = True
    for msg_chunk, metadata in graph_msg.stream(input_msg, stream_mode="messages"):
        # V1: messages 模式返回 (message_chunk, metadata) 元组
        # msg_chunk: AIMessageChunk 对象，主要字段有 .content (str, token文本), .type (str, "AIMessageChunk"),
        #            .tool_calls (list, 工具调用信息), .additional_kwargs (dict, 额外参数)
        # metadata: dict，重要字段包括:
        #   - "langgraph_node": str, 产生该 token 的节点名称
        #   - "langgraph_step": int, 当前步骤编号
        #   - "langgraph_triggers": list[str], 触发该节点的上游节点
        #   - "langgraph_path": tuple, 当前执行路径
        #   - "langgraph_checkpoint_ns": str, checkpoint 命名空间
        #   - "ls_model_name": str, 模型名称
        #   - "ls_provider": str, 模型提供商 (如 "ollama")
        #   - "ls_tags": list[str], 模型标签
        if first_chunk:
            print(f"  [metadata keys]: {list(metadata.keys())}")
            print(f"  [metadata sample]: langgraph_node={metadata.get('langgraph_node')}, "
                  f"langgraph_step={metadata.get('langgraph_step')}, "
                  f"langgraph_triggers={metadata.get('langgraph_triggers')}, "
                  f"ls_model_name={metadata.get('ls_model_name')}, "
                  f"ls_provider={metadata.get('ls_provider')}")
            print(f"  [msg_chunk type]: {type(msg_chunk).__name__}")
            first_chunk = False
        if msg_chunk.content:
            print(msg_chunk.content, end="", flush=True)
    print()

    # ======================= 4. checkpoints / tasks / debug 模式（需要 checkpointer） =======================
    print("\n" + "=" * 30 + " V1: checkpoints / tasks / debug 模式 " + "=" * 30)

    class CkState(TypedDict):
        topic: str
        result: str

    def step_a(state: CkState) -> Dict[str, str]:
        return {"result": f"step-a: {state['topic']}"}

    def step_b(state: CkState) -> Dict[str, str]:
        return {"result": state["result"] + " -> step-b"}

    graph_ck: CompiledStateGraph = (
        StateGraph(CkState)
        .add_node("step_a", step_a)
        .add_node("step_b", step_b)
        .add_edge(START, "step_a")
        .add_edge("step_a", "step_b")
        .add_edge("step_b", END)
        .compile(checkpointer=MemorySaver())
    )

    ck_config: RunnableConfig = {"configurable": {"thread_id": "ck-1"}}

    # --- checkpoints 模式：每个步骤后输出 checkpoint 事件 ---
    print("\n--- checkpoints 模式 ---")
    input_ck = {"topic": "demo", "result": ""}
    print(f"  input: {input_ck}, config: {ck_config}")
    for chunk in graph_ck.stream(
        input_ck, config=ck_config, stream_mode="checkpoints"
    ):
        # V1: checkpoints 模式返回 checkpoint 数据（与 get_state() 格式相同）
        print(f"  checkpoint: {chunk}")

    # --- tasks 模式：任务开始/完成事件 ---
    print("\n--- tasks 模式 ---")
    input_tasks = {"topic": "demo", "result": ""}
    print(f"  input: {input_tasks}, config: {ck_config}")
    for chunk in graph_ck.stream(
        input_tasks, config=ck_config, stream_mode="tasks"
    ):
        # V1: tasks 模式返回任务事件
        print(f"  task: {chunk}")

    # --- debug 模式：尽可能多的调试信息 ---
    print("\n--- debug 模式 ---")
    input_debug = {"topic": "demo", "result": ""}
    print(f"  input: {input_debug}, config: {ck_config}")
    for chunk in graph_ck.stream(
        input_debug, config=ck_config, stream_mode="debug"
    ):
        # V1: debug 模式返回详细的调试信息
        print(f"  debug: {chunk}")

    # ======================= 5. 多模式同时使用 =======================
    print("\n" + "=" * 30 + " V1: 多模式同时使用 " + "=" * 30)

    print("\n--- stream_mode=['updates', 'custom'] ---")
    input_multi = {"query": "multi-mode", "answer": ""}
    print(f"  input: {input_multi}")
    for chunk in graph_custom.stream(
        input_multi, stream_mode=["updates", "custom"]
    ):
        # V1: 多模式时返回 (mode, data) 元组
        print(f"  chunk: {chunk}")

    # ======================= 6. 子图 (subgraphs) 模式 =======================
    print("\n" + "=" * 30 + " V1: 子图 (subgraphs) 模式 " + "=" * 30)

    class SubState(TypedDict):
        foo: str
        bar: str

    def sub_node_1(state: SubState) -> Dict[str, str]:
        return {"bar": "bar-from-sub"}

    def sub_node_2(state: SubState) -> Dict[str, str]:
        return {"foo": state["foo"] + "+" + state["bar"]}

    subgraph_builder: StateGraph = StateGraph(SubState)
    subgraph_builder.add_node("sub_node_1", sub_node_1)
    subgraph_builder.add_node("sub_node_2", sub_node_2)
    subgraph_builder.add_edge(START, "sub_node_1")
    subgraph_builder.add_edge("sub_node_1", "sub_node_2")
    subgraph_builder.add_edge("sub_node_2", END)
    subgraph: CompiledStateGraph = subgraph_builder.compile()

    class ParentState(TypedDict):
        foo: str

    def parent_node(state: ParentState) -> Dict[str, str]:
        return {"foo": "hi! " + state["foo"]}

    parent_graph: CompiledStateGraph = (
        StateGraph(ParentState)
        .add_node("parent_node", parent_node)
        .add_node("sub_node", subgraph)  # 将子图作为节点添加
        .add_edge(START, "parent_node")
        .add_edge("parent_node", "sub_node")
        .add_edge("sub_node", END)
        .compile()
    )

    print("\n--- subgraphs=True, stream_mode='updates' ---")
    input_sub = {"foo": "foo"}
    print(f"  input: {input_sub}")
    for chunk in parent_graph.stream(
        input_sub, stream_mode="updates", subgraphs=True
    ):
        # V1: 子图模式返回 (namespace, data) 元组，namespace 标识来源图
        print(f"  chunk: {chunk}")


def graph_stream_usage_v2() -> None:
    """
    展示 LangGraph 的 Stream API V2 使用。
    LangGraph v1.1+ 版本引入了新的统一Stream返回格式，可以通过 version="v2" 参数指定。

    V2 版本的输出格式特点：
    - 所有 chunk 都是统一的 StreamPart dict，包含三个字段：
      - "type": 字符串，标识 stream mode（"values" | "updates" | "messages" | "custom" | "checkpoints" | "tasks" | "debug"）
      - "ns": 元组，命名空间（子图事件时填充，根图为空元组）
      - "data": 实际负载数据，类型随 mode 不同而变化
    - 无论单模式、多模式、子图，格式始终一致，通过 chunk["type"] 区分
    - 支持类型窄化（type narrowing），编辑器/类型检查器可以正确推断 data 类型
    - invoke() 返回 GraphOutput 对象（含 .value 和 .interrupts 属性）
    - Pydantic/dataclass 状态在 values 模式下自动强制转换为对应类型
    """

    # ======================= 1. updates / values 模式（fake demo） =======================
    print("=" * 30 + " V2: updates / values 模式 " + "=" * 30)

    class SimpleState(TypedDict):
        topic: str
        result: str

    def refine_topic(state: SimpleState) -> Dict[str, str]:
        return {"topic": state["topic"] + " and cats"}

    def generate_result(state: SimpleState) -> Dict[str, str]:
        return {"result": f"This is a result about {state['topic']}"}

    graph: CompiledStateGraph = (
        StateGraph(SimpleState)
        .add_node("refine_topic", refine_topic)
        .add_node("generate_result", generate_result)
        .add_edge(START, "refine_topic")
        .add_edge("refine_topic", "generate_result")
        .add_edge("generate_result", END)
        .compile()
    )

    # --- updates 模式 ---
    print("\n--- updates 模式 ---")
    input_updates = {"topic": "ice cream", "result": ""}
    print(f"  input: {input_updates}")
    for chunk in graph.stream(
        input_updates, stream_mode="updates", version="v2"
    ):
        # V2: 统一格式，chunk["type"] == "updates"，chunk["data"] 是 {node_name: update_dict}
        if chunk["type"] == "updates":
            for node_name, state_update in chunk["data"].items():
                print(f"  Node '{node_name}' updated: {state_update}")

    # --- values 模式 ---
    print("\n--- values 模式 ---")
    input_values = {"topic": "ice cream", "result": ""}
    print(f"  input: {input_values}")
    for chunk in graph.stream(
        input_values, stream_mode="values", version="v2"
    ):
        # V2: chunk["type"] == "values"，chunk["data"] 是完整 state dict
        if chunk["type"] == "values":
            print(f"  State: topic={chunk['data']['topic']}, result={chunk['data']['result']}")

    # ======================= 2. custom 模式（fake demo） =======================
    print("\n" + "=" * 30 + " V2: custom 模式 " + "=" * 30)

    class CustomState(TypedDict):
        query: str
        answer: str

    def custom_node(state: CustomState) -> Dict[str, str]:
        writer = get_stream_writer()
        writer({"progress": "step-1: thinking..."})
        writer({"progress": "step-2: generating..."})
        return {"answer": f"Answer to: {state['query']}"}

    graph_custom: CompiledStateGraph = (
        StateGraph(CustomState)
        .add_node("custom_node", custom_node)
        .add_edge(START, "custom_node")
        .add_edge("custom_node", END)
        .compile()
    )

    print("\n--- custom 模式 ---")
    input_custom = {"query": "hello", "answer": ""}
    print(f"  input: {input_custom}")
    for chunk in graph_custom.stream(
        input_custom, stream_mode="custom", version="v2"
    ):
        # V2: chunk["type"] == "custom"，chunk["data"] 是 writer 发送的 dict
        if chunk["type"] == "custom":
            print(f"  Custom event: {chunk['data']}")

    # ======================= 3. messages 模式（需要调用模型） =======================
    print("\n" + "=" * 30 + " V2: messages 模式 " + "=" * 30)

    class MsgState(TypedDict):
        topic: str
        joke: str

    client_chat: BaseChatModel = get_client_chat()

    def call_model(state: MsgState) -> Dict[str, str]:
        response: AIMessage = client_chat.invoke(
            [{"role": "user", "content": f"Generate a short joke about {state['topic']}"}]
        )
        return {"joke": response.content}

    graph_msg: CompiledStateGraph = (
        StateGraph(MsgState)
        .add_node("call_model", call_model)
        .add_edge(START, "call_model")
        .add_edge("call_model", END)
        .compile()
    )

    print("\n--- messages 模式（LLM token 级别流式输出） ---")
    input_msg = {"topic": "ice cream", "joke": ""}
    print(f"  input: {input_msg}")
    first_chunk = True
    for chunk in graph_msg.stream(
        input_msg, stream_mode="messages", version="v2"
    ):
        # V2: chunk["type"] == "messages"，chunk["data"] 是 (message_chunk, metadata) 元组
        if chunk["type"] == "messages":
            msg_chunk, metadata = chunk["data"]
            if first_chunk:
                print(f"  [chunk keys]: {list(chunk.keys())}")  # ['type', 'ns', 'data']
                print(f"  [metadata keys]: {list(metadata.keys())}")
                print(f"  [metadata sample]: langgraph_node={metadata.get('langgraph_node')}, "
                      f"langgraph_step={metadata.get('langgraph_step')}, "
                      f"langgraph_triggers={metadata.get('langgraph_triggers')}, "
                      f"ls_model_name={metadata.get('ls_model_name')}, "
                      f"ls_provider={metadata.get('ls_provider')}")
                print(f"  [msg_chunk type]: {type(msg_chunk).__name__}")
                first_chunk = False
            if msg_chunk.content:
                print(msg_chunk.content, end="", flush=True)
    print()

    # ======================= 4. checkpoints / tasks / debug 模式 =======================
    print("\n" + "=" * 30 + " V2: checkpoints / tasks / debug 模式 " + "=" * 30)

    class CkState(TypedDict):
        topic: str
        result: str

    def step_a(state: CkState) -> Dict[str, str]:
        return {"result": f"step-a: {state['topic']}"}

    def step_b(state: CkState) -> Dict[str, str]:
        return {"result": state["result"] + " -> step-b"}

    graph_ck: CompiledStateGraph = (
        StateGraph(CkState)
        .add_node("step_a", step_a)
        .add_node("step_b", step_b)
        .add_edge(START, "step_a")
        .add_edge("step_a", "step_b")
        .add_edge("step_b", END)
        .compile(checkpointer=MemorySaver())
    )

    ck_config: RunnableConfig = {"configurable": {"thread_id": "ck-v2-1"}}

    print("\n--- checkpoints 模式 ---")
    input_ck = {"topic": "demo", "result": ""}
    print(f"  input: {input_ck}, config: {ck_config}")
    for chunk in graph_ck.stream(
        input_ck, config=ck_config, stream_mode="checkpoints", version="v2"
    ):
        if chunk["type"] == "checkpoints":
            print(f"  checkpoint: {chunk['data']}")

    print("\n--- tasks 模式 ---")
    input_tasks = {"topic": "demo", "result": ""}
    print(f"  input: {input_tasks}, config: {ck_config}")
    for chunk in graph_ck.stream(
        input_tasks, config=ck_config, stream_mode="tasks", version="v2"
    ):
        if chunk["type"] == "tasks":
            print(f"  task: {chunk['data']}")

    print("\n--- debug 模式 ---")
    input_debug = {"topic": "demo", "result": ""}
    print(f"  input: {input_debug}, config: {ck_config}")
    for chunk in graph_ck.stream(
        input_debug, config=ck_config, stream_mode="debug", version="v2"
    ):
        if chunk["type"] == "debug":
            print(f"  debug: {chunk['data']}")

    # ======================= 5. 多模式同时使用 =======================
    print("\n" + "=" * 30 + " V2: 多模式同时使用 " + "=" * 30)

    print("\n--- stream_mode=['updates', 'custom'] ---")
    input_multi = {"query": "multi-mode", "answer": ""}
    print(f"  input: {input_multi}")
    for chunk in graph_custom.stream(
        input_multi, stream_mode=["updates", "custom"], version="v2"
    ):
        # V2: 多模式时格式不变，通过 chunk["type"] 区分
        if chunk["type"] == "updates":
            for node_name, state_update in chunk["data"].items():
                print(f"  [updates] Node '{node_name}': {state_update}")
        elif chunk["type"] == "custom":
            print(f"  [custom] {chunk['data']}")

    # ======================= 6. 子图 (subgraphs) 模式 =======================
    print("\n" + "=" * 30 + " V2: 子图 (subgraphs) 模式 " + "=" * 30)

    class SubState(TypedDict):
        foo: str
        bar: str

    def sub_node_1(state: SubState) -> Dict[str, str]:
        return {"bar": "bar-from-sub"}

    def sub_node_2(state: SubState) -> Dict[str, str]:
        return {"foo": state["foo"] + "+" + state["bar"]}

    subgraph_builder: StateGraph = StateGraph(SubState)
    subgraph_builder.add_node("sub_node_1", sub_node_1)
    subgraph_builder.add_node("sub_node_2", sub_node_2)
    subgraph_builder.add_edge(START, "sub_node_1")
    subgraph_builder.add_edge("sub_node_1", "sub_node_2")
    subgraph_builder.add_edge("sub_node_2", END)
    subgraph: CompiledStateGraph = subgraph_builder.compile()

    class ParentState(TypedDict):
        foo: str

    def parent_node(state: ParentState) -> Dict[str, str]:
        return {"foo": "hi! " + state["foo"]}

    parent_graph: CompiledStateGraph = (
        StateGraph(ParentState)
        .add_node("parent_node", parent_node)
        .add_node("sub_node", subgraph)
        .add_edge(START, "parent_node")
        .add_edge("parent_node", "sub_node")
        .add_edge("sub_node", END)
        .compile()
    )

    print("\n--- subgraphs=True, stream_mode='updates' ---")
    input_sub = {"foo": "foo"}
    print(f"  input: {input_sub}")
    for chunk in parent_graph.stream(
        input_sub, stream_mode="updates", subgraphs=True, version="v2"
    ):
        # V2: 子图事件通过 chunk["ns"] 标识来源，根图为空元组
        if chunk["type"] == "updates":
            if chunk["ns"]:
                print(f"  Subgraph {chunk['ns']}: {chunk['data']}")
            else:
                print(f"  Root: {chunk['data']}")


def graph_stream_event_v1_v2_usage() -> None:
    """
    展示 Graph 的 EventStream 使用。

    EventStream也有多个版本，由 version 参数控制：
    - version="v1" / "v2": 实际转发给底层的 langchain_core.runnables.base.Runnable 类的对应方法。
    - version="v3": LangGraph内部实现，参见下面的示例。

    :return:
    """


def graph_stream_event_v3_usage() -> None:
    """
    展示 Graph 的 EventStream-v3 基本使用。
    EventStream 是 LangGraph v1.2 新增的推荐流式 API，通过 stream_events() / astream_events() 方法使用。

    这里主要介绍 version="v3" 版本。

    EventStream 是基于Stream API的高层抽象：
    - Stream API 返回的是Graph底层Pregel引擎的原始执行事件
    - EventStream 在StreamAPI基础上进行了封装，新增了 EventRouter 和 StreamTransformer，
      用于将原始事件转换为更易用的类型化投影（typed projections）。

    与 stream() 的 stream_mode 方式不同，EventStream(v3版本) 返回一个 GraphRunStream 对象，提供类型化的投影（projections）：
    - stream: 迭代所有原始协议事件（ProtocolEvent）
    - stream.messages: 流式传输聊天模型消息和 token 增量
    - stream.values: 迭代状态快照，并等待最终值
    - stream.output: 等待最终输出
    - stream.subgraphs: 发现和观察嵌套图执行
    - stream.interrupts: 检查 HIL 中断负载
    - stream.interrupted: 检查运行是否因人工输入而暂停
    - stream.extensions: 消费自定义流转换器投影

    多个消费者可以并发读取这些投影，互不干扰。

    底层架构：
    Pregel 引擎 → 原始事件 (updates/values/messages/custom/...) → Event Router → Stream Transformers → Event Stream (typed projections)
    """
    client_chat: BaseChatModel = get_client_chat()

    # ======================= 1. 基本使用：stream.messages + stream.output =======================
    print("=" * 30 + " EventStream: 基本使用 (messages + output) " + "=" * 30)

    class MsgState(TypedDict):
        topic: str
        joke: str

    def call_model(state: MsgState) -> Dict[str, str]:
        response: AIMessage = client_chat.invoke(
            [{"role": "user", "content": f"Generate a short joke about {state['topic']}"}]
        )
        return {"joke": response.content}

    graph: CompiledStateGraph = (
        StateGraph(MsgState)
        .add_node("call_model", call_model)
        .add_edge(START, "call_model")
        .add_edge("call_model", END)
        .compile()
    )

    input_msg = {"topic": "ice cream", "joke": ""}
    print(f"  input: {input_msg}")

    # version="v2"/"v1" 时返回的是 Iterator[StreamEvent] | Iterator[Any]
    # version="v3" 时，stream_events() 返回 Run 对象
    stream: GraphRunStream = graph.stream_events(input_msg, version="v3")
    print("  type(stream):", type(stream))

    # --- stream.messages: 流式传输 LLM token ---
    print("\n--- stream.messages (LLM token 级别流式输出) ---")
    for message in stream.messages:
        # message.text 是可迭代的，逐 token 输出
        for token in message.text:
            print(token, end="", flush=True)
    print()

    # --- stream.output: 获取最终状态 ---
    final_state = stream.output
    print(f"\n--- stream.output (最终状态) ---")
    print(f"  final_state: {final_state}")

    # ======================= 2. stream.values：状态快照 =======================
    print("\n" + "=" * 30 + " EventStream: stream.values " + "=" * 30)

    class SimpleState(TypedDict):
        topic: str
        result: str

    def refine_topic(state: SimpleState) -> Dict[str, str]:
        return {"topic": state["topic"] + " and cats"}

    def generate_result(state: SimpleState) -> Dict[str, str]:
        return {"result": f"This is a result about {state['topic']}"}

    graph2: CompiledStateGraph = (
        StateGraph(SimpleState)
        .add_node("refine_topic", refine_topic)
        .add_node("generate_result", generate_result)
        .add_edge(START, "refine_topic")
        .add_edge("refine_topic", "generate_result")
        .add_edge("generate_result", END)
        .compile()
    )

    input_values = {"topic": "ice cream", "result": ""}
    print(f"  input: {input_values}")
    stream2: GraphRunStream = graph2.stream_events(input_values, version="v3")

    print("\n--- stream.values (状态快照) ---")
    for snapshot in stream2.values:
        print(f"  snapshot: {snapshot}")

    print(f"\n--- stream.output ---")
    print(f"  final: {stream2.output}")

    # ======================= 3. HIL 中断检测 =======================
    print("\n" + "=" * 30 + " EventStream: HIL 中断检测 " + "=" * 30)

    class HILState(TypedDict):
        msg: str

    def interrupt_node(state: HILState) -> Dict[str, str]:
        human_response = interrupt(value={"question": "请确认是否继续?"})
        return {"msg": f"received: {human_response}"}

    graph_hil: CompiledStateGraph = (
        StateGraph(HILState)
        .add_node("interrupt_node", interrupt_node)
        .add_edge(START, "interrupt_node")
        .add_edge("interrupt_node", END)
        .compile(checkpointer=MemorySaver())
    )

    hil_config: RunnableConfig = {"configurable": {"thread_id": "hil-ev-1"}}
    input_hil = {"msg": ""}
    print(f"  input: {input_hil}")

    stream_hil: GraphRunStream = graph_hil.stream_events(input_hil, config=hil_config, version="v3")

    # 消费 stream 以触发中断
    for _ in stream_hil.values:
        pass

    # stream.interrupted: 检查是否因中断而暂停
    if stream_hil.interrupted:
        print(f"\n  [interrupted] True — 图已暂停，等待人工输入")
        # stream.interrupts: 获取中断负载
        for interrupt_item in stream_hil.interrupts:
            print(f"  interrupt value: {interrupt_item.value}")

        # 通过 Command 恢复执行
        stream_hil_resume = graph_hil.stream_events(
            Command(resume="确认继续"), config=hil_config, version="v3"
        )
        print(f"  resumed output: {stream_hil_resume.output}")
    else:
        print(f"\n  [interrupted] False — 图已完成，无需人工输入")


    # ======================= 3. stream.subgraphs：子图观察 =======================
    print("\n" + "=" * 30 + " EventStream: stream.subgraphs " + "=" * 30)

    class SubState(TypedDict):
        foo: str
        bar: str

    def sub_node_1(state: SubState) -> Dict[str, str]:
        return {"bar": "bar-from-sub"}

    def sub_node_2(state: SubState) -> Dict[str, str]:
        return {"foo": state["foo"] + "+" + state["bar"]}

    subgraph_builder: StateGraph = StateGraph(SubState)
    subgraph_builder.add_node("sub_node_1", sub_node_1)
    subgraph_builder.add_node("sub_node_2", sub_node_2)
    subgraph_builder.add_edge(START, "sub_node_1")
    subgraph_builder.add_edge("sub_node_1", "sub_node_2")
    subgraph_builder.add_edge("sub_node_2", END)
    subgraph: CompiledStateGraph = subgraph_builder.compile(name="MySubgraph")

    class ParentState(TypedDict):
        foo: str

    def parent_node(state: ParentState) -> Dict[str, str]:
        return {"foo": "hi! " + state["foo"]}

    parent_graph: CompiledStateGraph = (
        StateGraph(ParentState)
        .add_node("parent_node", parent_node)
        .add_node("sub_node", subgraph)
        .add_edge(START, "parent_node")
        .add_edge("parent_node", "sub_node")
        .add_edge("sub_node", END)
        .compile()
    )

    input_sub = {"foo": "foo"}
    print(f"  input: {input_sub}")

    stream_sub: GraphRunStream = parent_graph.stream_events(input_sub, version="v3")

    print("\n--- stream.subgraphs (子图观察) ---")
    for sub in stream_sub.subgraphs:
        # sub.graph_name: 子图的名称
        # sub.path: 子图在父图中的路径
        print(f"  subgraph: name={sub.graph_name}, path={sub.path}")
        # 也可以访问子图的 values
        for snapshot in sub.values:
            print(f"    sub-snapshot: {snapshot}")

    print(f"\n--- stream.output ---")
    print(f"  final: {stream_sub.output}")


def graph_stream_event_v3_advanced_usage():
    """
    展示 Graph 的 EventStream 的进阶使用。
    EventStream 是 LangGraph v1.2 新增的推荐流式 API，通过 stream_events() / astream_events() 方法使用。
    :return:
    """
    class SimpleState(TypedDict):
        topic: str
        result: str

    def refine_topic(state: SimpleState) -> Dict[str, str]:
        return {"topic": state["topic"] + " and cats"}

    def generate_result(state: SimpleState) -> Dict[str, str]:
        return {"result": f"This is a result about {state['topic']}"}

    graph: CompiledStateGraph = (
        StateGraph(SimpleState)
        .add_node("refine_topic", refine_topic)
        .add_node("generate_result", generate_result)
        .add_edge(START, "refine_topic")
        .add_edge("refine_topic", "generate_result")
        .add_edge("generate_result", END)
        .compile()
    )

    input_values = {"topic": "ice cream", "result": ""}

    # ======================= 1. stream.interleave()：多投影同步消费 =======================
    print("\n" + "=" * 30 + " EventStream: stream.interleave() " + "=" * 30)
    print(f"  input: {input_values}")

    stream_inter = graph.stream_events(input_values, version="v3")

    print("\n--- interleave('values', 'messages') ---")
    # interleave() 按严格到达顺序交错消费多个投影
    for name, item in stream_inter.interleave("values"):
        if name == "values":
            print(f"  [values] keys={list(item.keys()) if isinstance(item, dict) else item}")

    # ======================= 2. 原始协议事件迭代 =======================
    print("\n" + "=" * 30 + " EventStream: 原始协议事件 " + "=" * 30)
    print(f"  input: {input_values}")
    stream_proto: GraphRunStream = graph.stream_events(input_values, version="v3")

    print("\n--- 直接迭代 stream（原始 ProtocolEvent） ---")
    event_count: int = 0
    for event in stream_proto:
        # ProtocolEvent 结构: {"seq": int, "method": str, "params": {"namespace": [...], "timestamp": int, "data": ...}}
        # method 即 channel 名称: "values", "updates", "messages", "custom", "tools", "lifecycle", ...
        if event_count < 3:  # 只展示前3个事件
            print(f"  event: method={event['method']}, "
                  f"namespace={event['params']['namespace']}, "
                  f"seq={event['seq']}")
        event_count += 1
    print(f"  ... total events: {event_count}")


    # ======================= 3. 自定义 StreamTransformer =======================
    print("\n" + "=" * 30 + " EventStream: 自定义 StreamTransformer " + "=" * 30)

    class ProgressTransformer(StreamTransformer):
        """
        自定义转换器：监听 custom 通道事件，将进度信息收集到 StreamChannel 中。

        StreamTransformer 接口：
        - init() -> dict: 创建投影对象，返回的 dict 会出现在 stream.extensions 下
        - process(event: ProtocolEvent) -> bool: 处理每个协议事件，返回 False 可抑制该事件
        - finalize() -> None: 运行成功结束后调用
        - fail(err: BaseException) -> None: 运行失败时调用
        - required_stream_modes: 声明需要的 Pregel stream mode，未声明的 mode 不会被发出
        """
        required_stream_modes: tuple[str, ...] = ("custom",)

        def __init__(self, scope: tuple[str, ...] = ()) -> None:
            super().__init__(scope)
            # StreamChannel: 投影原语，用于流式传输值
            # 传入 name 参数时，push() 的值也会作为 custom:<name> 事件流入主事件流
            self.progress: StreamChannel[dict] = StreamChannel[dict]("progress")

        def init(self) -> dict:
            return {"progress": self.progress}

        def process(self, event: ProtocolEvent) -> bool:
            if event["method"] == "custom":
                data = event["params"]["data"]
                self.progress.push(data)
            return True

    class CustomState(TypedDict):
        query: str
        answer: str

    def custom_node(state: CustomState) -> Dict[str, str]:
        writer = get_stream_writer()
        writer({"step": 1, "msg": "thinking..."})
        writer({"step": 2, "msg": "generating..."})
        return {"answer": f"Answer to: {state['query']}"}

    graph_custom: CompiledStateGraph = (
        StateGraph(CustomState)
        .add_node("custom_node", custom_node)
        .add_edge(START, "custom_node")
        .add_edge("custom_node", END)
        .compile()
    )

    input_custom = {"query": "hello", "answer": ""}
    print(f"  input: {input_custom}")

    # 通过 transformers 参数注册自定义转换器
    stream_custom: GraphRunStream = graph_custom.stream_events(
        input_custom, version="v3", transformers=[ProgressTransformer]
    )

    print("\n--- stream.extensions['progress'] (自定义投影) ---")
    for item in stream_custom.extensions["progress"]:
        print(f"  progress: {item}")

    print(f"\n--- stream.output ---")
    print(f"  final: {stream_custom.output}")

    # ======================= 4. ToolCallTransformer（内置） =======================
    print("\n" + "=" * 30 + " EventStream: ToolCallTransformer " + "=" * 30)

    @tool(description="使用龙球(DragonBall)算法计算两个数字的结果")
    def dragon_ball_algorithm(x: Annotated[int, "第一个数字"], y: Annotated[int, "第二个数字"]) -> int:
        return x + y + 1

    tools: list = [dragon_ball_algorithm]
    tool_node: ToolNode = ToolNode(tools=tools)
    client_chat_tool: BaseChatModel = get_client_chat().bind_tools(tools=tools)
    memory: MemorySaver = MemorySaver()
    agent: CompiledStateGraph = create_react_agent(
        name='ReAct-Agent', model=client_chat_tool, tools=tool_node, checkpointer=memory
    )

    input_agent: dict[str, list[BaseMessage]] = {
        "messages": [
            SystemMessage(content='你是一个算术专家'),
            HumanMessage(content='请使用龙球(DragonBall)算法计算一下 2019 和 2022 的结果'),
        ]
    }
    config: RunnableConfig = {"configurable": {"thread_id": "evt-1"}}
    print(f"  input: {input_agent}")

    # ToolCallTransformer 是内置转换器，注册后可通过 stream.tool_calls 访问工具调用信息
    stream_agent: GraphRunStream = agent.stream_events(
        input_agent, config=config, version="v3", transformers=[ToolCallTransformer]
    )

    print("\n--- stream.tool_calls (工具调用投影) ---")
    for tool_call in stream_agent.tool_calls:
        print(f"  tool_call: name={tool_call.tool_name}, input={tool_call.input}")

    print(f"\n--- stream.output ---")
    final: dict = stream_agent.output
    if isinstance(final, dict) and "messages" in final:
        for msg in final["messages"]:
            msg.pretty_print()



# %% ======================= Graph Node 自定义 =======================
def graph_custom_node_with_class_usage():
    """
    展示如何自定义 Graph 里的node。
    参考官方文档[Graph API concepts](https://langchain-ai.github.io/langgraph/concepts/low_level/).
    LangGraph 里的 Node，一般是一个 Python function，入参是自定义的 State，返回的是更新后的 State 或者 State 里的某个key的值。
    但是有时候为了执行一些复杂逻辑，Node 也可以定义成一个 class，此时有两种做法：
    1. 类似于 chatbot_tool_usage_manual 示例中那样，定义一个 class，需要实现其中的 __call__ 方法，使其称为一个 Callable 对象，这种方式比较简单
    2. 类似于 chatbot_tool_usage_prebuilt 示例中那样，参考其中 ToolNode 类的实现，继承 langgraph 提供的 RunnableCallable 抽象类，实现
    """
    class State(TypedDict):
        messages: Annotated[list, add_messages]

    class CustomNode:
        def __init__(self, name: str) -> None:
            self.name = f"<CustomNode:{name}>"

        def __call__(self, inputs: State):
            print(f"{self.name} called with inputs: {inputs}")
            return {"messages": [f"{self.name} says: Hello!"]}

    class RunnableNode(RunnableCallable):
        def __init__(self, name: str) -> None:
            name = f"<RunnableNode:{name}>"
            # RunnableCallable 的 __init__ 方法里，只有 func 参数是必须的，其他都可选，这里是仿照的 ToolsNode 的实现
            super().__init__(func=self._func, name=name)
            self.name = name

        def _func(self, inputs: State):
            """同步调用函数"""
            print(f"{self.name} called with inputs: {inputs}")
            return {"messages": [f"{self.name} says: Welcome!"]}

    graph = StateGraph(state_schema=State)
    graph.add_node(node="custom_node", action=CustomNode(name="SomeNode"))
    graph.add_node(node="runnable_node", action=RunnableNode(name="SomeRunNode"))
    graph.set_entry_point("custom_node")
    graph.add_edge("custom_node", "runnable_node")
    graph.set_finish_point("runnable_node")
    compile_graph: CompiledStateGraph = graph.compile(name='GraphWithCustomNode')

    res = compile_graph.invoke(input={"messages": [HumanMessage(content="Hi")]})
    print(res)


def show_graph(graph: CompiledStateGraph):
    """
    绘制LangGraph 的 Graph 图结构.
    参考官方文档[Graph API -> Use the graph API -> Visualize your graph](https://docs.langchain.com/oss/python/langgraph/use-graph-api#visualize-your-graph)
    """
    try:
        from IPython.display import Image, display
        # display(Image(graph.get_graph().draw_mermaid_png()))
        img = Image(graph.get_graph().draw_mermaid_png())
        with open(f"{graph.get_name()}.png", 'wb') as f:
            f.write(img.data)
    except Exception as e:
        # This may require some extra dependencies and is optional
        print(e)


# %% ======================= Main =======================
def main():
    # stateful_graph_usage()
    # message_graph_usage()
    # graph_conditional_usage()
    # graph_checkpoint_usage()
    # graph_store_usage()
    # graph_dynamic_interrupt_usage()
    # graph_fixed_breakpoint_usage()
    # chatbot_example()
    # chatbot_tool_usage_manual()
    # chatbot_tool_usage_prebuilt()
    # react_agent_usage()
    # graph_fault_tolerance_timeout_usage()
    # graph_fault_tolerance_usage()
    # graph_stream_usage_v1()
    # graph_stream_usage_v2()
    # graph_stream_event_v1_v2_usage()
    graph_stream_event_v3_usage()
    graph_stream_event_v3_advanced_usage()
    # graph_custom_node_with_class_usage()


if __name__ == '__main__':
    main()
