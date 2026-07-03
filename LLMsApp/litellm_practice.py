"""
LiteLLM使用
"""
# %% ===================================================================================================================
from typing import List, Dict, Tuple
import os
import json
import asyncio
import anyio
# ------ LiteLLM 请求封装函数 ------
# 大部分请求函数的实现都在 litellm.main.py 中，但可以从顶层直接导入
from litellm import (
    # --- completion 系列是主要的使用入口 ---
    completion, acompletion,
    completion_with_retries, acompletion_with_retries,
    batch_completion, batch_completion_models, batch_completion_models_all_responses,
    responses, aresponses, responses_with_retries, aresponses_with_retries,
    embedding, aembedding,
    text_completion, atext_completion,
    image_generation, aimage_generation,
    transcription, atranscription,
    speech, aspeech,
)
# ------ LiteLLM 工具函数 ------
# 大部分工具函数可以从直接 litellm 导入声明，但是实际实现都是在 litellm.utils.py 中
# from litellm import (
from litellm.utils import (
    check_valid_key, get_valid_models, validate_environment,
    get_standard_openai_params, get_supported_openai_params,
    supports_response_schema,
    supports_function_calling, supports_parallel_function_calling,
    trim_messages,
)
# ------ LiteLLM 类型 ------
# litellm.types 这个模块没有顶级声明，似乎不是对外公开的类型说明，常用的类型反倒是在 litellm.utils.py 中
# from litellm.types.responses.main import OutputText
from litellm.utils import (
    ModelInfo, ModelResponse, ModelResponseStream, CustomStreamWrapper
)
# ------ LiteLLM 异常 ------
# 大部分异常也可以直接从 litellm 导入声明
from litellm.exceptions import (
    AuthenticationError, RateLimitError, APIError
)
# ------ LiteLLM 矢量数据库 ------
from litellm.vector_stores.vector_store_registry import VectorStoreRegistry, LiteLLM_ManagedVectorStore

# %% ===================================================================================================================
# --- Ollama 本地部署 ---
API_KEY = 'Empty'
LLM_URL = 'http://localhost:11434'
# 对于LiteLLM，模型名称格式为：Provider/模型名称
MODEL = 'ollama/qwen2.5:7b'
# MODEL = 'ollama/qwen3:8b'
# MODEL = 'ollama/qwen2.5:14b'
# MODEL = 'ollama/qwen3:14b'
MODEL_EMBEDDING = 'ollama/bge-m3:567m'


# %% ===================================================================================================================
def litellm_completion_basic_usage():
    """
    展示 LiteLLM 基本使用 - 同步API
    :return:
    """
    print("===> litellm_completion_basic_usage")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请介绍下你最擅长Top-10编程语言"},
    ]

    print("--------- Non Stream Mode --------")
    res: ModelResponse = completion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
    )
    print("type(res):", type(res))
    # ModelResponse 示例如下：
    # {
    #     "id": "chatcmpl-548eb698-a1bf-4679-9cc0-55dcccbc3e97",
    #     "created": 1783067016,
    #     "model": "ollama/qwen2.5:7b",
    #     "object": "chat.completion",
    #     "system_fingerprint": None,
    #     "choices":
    #     [
    #         {
    #             "finish_reason": "stop",
    #             "index": 0,
    #             "message":
    #             {
    #                 "content": "当然，我可以为您介绍目前较为流行和广泛使用的前十大编程语言。...",
    #                 "role": "assistant",
    #                 "tool_calls": None,
    #                 "function_call": None,
    #                 "reasoning_content": None
    #             }
    #         }
    #     ],
    #     "usage":
    #     {
    #         "completion_tokens": 510,
    #         "prompt_tokens": 54,
    #         "total_tokens": 564,
    #         "completion_tokens_details": None,
    #         "prompt_tokens_details": None
    #     }
    # }
    # print("res:", res)
    # print("res.json():\n", res.json())
    print("res.id:", res.id)
    print("res.model:", res.model)
    print("res.object:", res.object)
    print("res.usage:", res.usage)
    # print("res.choices:", res.choices)
    print("res.choices:")
    for choice in res.choices:
        print("  choice.index:", choice.index)
        print("  choice.finish_reason:", choice.finish_reason)
        # print("  choice.message:", choice.message)
        print("  choice.message:")
        print("    choice.message.role:", choice.message.role)
        print("    choice.message.function_call:", choice.message.function_call)
        print("    choice.message.tool_calls:", choice.message.tool_calls)
        print("    choice.message.reasoning_content:", choice.message.reasoning_content)
        print("    choice.message.content:\n", choice.message.content)
        print("  ---")

    print("\n--------- Stream Mode Detail --------")
    res_stream: CustomStreamWrapper = completion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        stream=True
    )
    print("type(res_stream):", type(res_stream))
    print("res_stream.chunks:")
    for chunk_num, chunk in enumerate(res_stream, start=1):
        print(f"chunk[{chunk_num}]")
        if chunk_num == 1:
            print("type(chunk):", type(chunk))  # ModelResponseStream
        # print("chunk.json():\n", chunk.json())
        print("  chunk.id:", chunk.id)
        print("  chunk.model:", chunk.model)
        print("  chunk.object:", chunk.object)
        # print("  chunk.choices:", chunk.choices)
        print("  chunk.choices:")
        for choice_num, choice in enumerate(chunk.choices):
            print("    choice_num:", choice_num)
            print("    choice.finish_reason:", choice.finish_reason)
            print("    choice.delta:", choice.delta)
            print("    choice.delta.role:", choice.delta.role)
            print("    choice.delta.content:", choice.delta.content)
        print("---")


    print("\n--------- Stream Mode --------")
    for chunk in completion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        stream=True
    ):
        print(chunk.choices[0].delta.content or "", end="")
    print()


async def litellm_completion_basic_usage_async():
    """
    展示 LiteLLM 基本使用 - 异步API
    :return:
    """
    print("===> litellm_completion_basic_usage_async")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请介绍下你最擅长Top-10编程语言"},
    ]

    print("--------- Async Non Stream Mode --------")
    # 异步非Stream模式下，除了改为使用 acompletion + await 之外，拿到的结果也是同步API返回的 ModelResponse，因此剩下的使用方式都一样。
    res: ModelResponse = await acompletion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages
    )
    print("res.id:", res.id)
    print("res.model:", res.model)
    print("res.object:", res.object)
    print("res.usage:", res.usage)
    # print("res.choices:", res.choices)
    print("res.choices:")
    for choice in res.choices:
        print("  choice.index:", choice.index)
        print("  choice.finish_reason:", choice.finish_reason)
        # print("  choice.message:", choice.message)
        print("  choice.message:")
        print("    choice.message.role:", choice.message.role)
        print("    choice.message.function_call:", choice.message.function_call)
        print("    choice.message.tool_calls:", choice.message.tool_calls)
        print("    choice.message.reasoning_content:", choice.message.reasoning_content)
        print("    choice.message.content:\n", choice.message.content)
        print("  ---")

    print("\n--------- Async Stream Mode Detail --------")
    # 异步Stream模式下，拿到的结果也是同步API返回的 ModelResponseStream
    res_stream: CustomStreamWrapper = await acompletion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        stream=True
    )
    print("type(res_stream):", type(res_stream))
    print("res_stream.chunks:")
    # 但此时的 CustomStreamWrapper 是异步迭代器，不能使用 for 迭代，必须使用 async for 迭代 -------- KEY
    chunk_num = 0
    async for chunk in res_stream:
        chunk_num += 1
        print(f"chunk[{chunk_num}]")
        if chunk_num == 1:
            print("type(chunk):", type(chunk))  # ModelResponseStream
        # print("chunk.json():\n", chunk.json())
        print("  chunk.id:", chunk.id)
        print("  chunk.model:", chunk.model)
        print("  chunk.object:", chunk.object)
        # print("  chunk.choices:", chunk.choices)
        print("  chunk.choices:")
        for choice_num, choice in enumerate(chunk.choices):
            print("    choice_num:", choice_num)
            print("    choice.finish_reason:", choice.finish_reason)
            print("    choice.delta:", choice.delta)
            print("    choice.delta.role:", choice.delta.role)
            print("    choice.delta.content:", choice.delta.content)
        print("---")

    print("\n--------- Async Stream Mode --------")
    async for chunk in await acompletion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        stream=True
    ):
        print(chunk.choices[0].delta.content or "", end="")
    print()


# %% ===================================================================================================================
def litellm_completion_with_retry_usage():
    """
    展示 LiteLLM completion 重试API - 同步
    completion_with_retries 在请求失败时会自动重试（默认重试次数由 num_retries 参数控制）。
    适用于网络不稳定或服务端偶发错误的场景。
    :return:
    """
    print("===> litellm_completion_with_retry_usage")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用一句话介绍Python编程语言"},
    ]

    # completion_with_retries 的参数和 completion 完全一致，只是增加了自动重试机制
    # num_retries: 重试次数，默认为 0（不重试），设置为正整数后会在遇到 APIError/Timeout/ServiceUnavailable 时自动重试
    res: ModelResponse = completion_with_retries(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        num_retries=3,  # 最多重试3次
    )
    print("type(res):", type(res))
    print("res.choices[0].message.content:\n", res.choices[0].message.content)

    # Stream 模式下同样支持重试
    print("\n--------- Stream Mode with Retry --------")
    for chunk in completion_with_retries(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        stream=True,
        num_retries=2,
    ):
        print(chunk.choices[0].delta.content or "", end="")
    print()


async def litellm_completion_with_retry_usage_async():
    """
    展示 LiteLLM completion 重试API - 异步
    acompletion_with_retries 是 completion_with_retries 的异步版本。
    :return:
    """
    print("===> litellm_completion_with_retry_usage_async")

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用一句话介绍Python编程语言"},
    ]

    # 异步非Stream模式
    res: ModelResponse = await acompletion_with_retries(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        num_retries=3,
    )
    print("res.choices[0].message.content:\n", res.choices[0].message.content)

    # 异步Stream模式
    print("\n--------- Async Stream Mode with Retry --------")
    async for chunk in await acompletion_with_retries(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        stream=True,
        num_retries=2,
    ):
        print(chunk.choices[0].delta.content or "", end="")
    print()



# %% ===================================================================================================================
def litellm_response_usage():
    """
    LiteLLM response API使用 - 同步
    responses() 是 LiteLLM 对 OpenAI /responses API 的封装，与 completion() 的主要区别：
    - 使用 input 参数（字符串）而非 messages 参数（列表）
    - 返回格式不同：output 数组中包含 output_text 类型的消息块
    - 使用 max_output_tokens 而非 max_tokens
    - 支持 previous_response_id 实现多轮对话状态管理
    注意：Ollama 不原生支持 /responses API，LiteLLM 会自动桥接到 /chat/completions。
    :return:
    """
    print("===> litellm_response_usage")

    # responses() 使用 input 参数，可以是字符串或列表
    print("--------- Non Stream Mode --------")
    res = responses(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        input="请用一句话介绍Python编程语言",
        max_output_tokens=200,
    )
    print("type(res):", type(res))
    # responses() 返回的格式与 completion() 不同，主要字段：
    # - id: 响应ID
    # - status: 状态（completed/in_progress等）
    # - output: 输出列表，每个元素有 type（如 "message"）和 content 列表
    # - usage: token使用量
    print("res.id:", res.id)
    print("res.status:", res.status)
    print("res.model:", res.model)
    print("res.usage:", res.usage)
    # 遍历 output 获取文本内容
    print("res.output:")
    for item in res.output:
        print("  item.type:", item.type)
        if hasattr(item, 'content') and item.content:
            for content_block in item.content:
                print("    content_block.type:", content_block.type)
                if hasattr(content_block, 'text'):
                    print("    content_block.text:", content_block.text)

    # Stream 模式
    print("\n--------- Stream Mode --------")
    for event in responses(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        input="请用一句话介绍Python编程语言",
        stream=True,
    ):
        # Stream 模式下每个 event 是一个响应事件
        if hasattr(event, 'type'):
            if event.type == "response.output_text.delta":
                print(event.delta or "", end="")
    print()


async def litellm_response_usage_async():
    """
    展示 LiteLLM response API使用 - 异步
    aresponses() 是 responses() 的异步版本。
    :return:
    """
    print("===> litellm_response_usage_async")

    # 异步非Stream模式
    print("--------- Async Non Stream Mode --------")
    res = await aresponses(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        input="请用一句话介绍Python编程语言",
        max_output_tokens=200,
    )
    print("res.id:", res.id)
    print("res.status:", res.status)
    for item in res.output:
        if hasattr(item, 'content') and item.content:
            for content_block in item.content:
                if hasattr(content_block, 'text'):
                    print("content:", content_block.text)

    # 异步Stream模式
    print("\n--------- Async Stream Mode --------")
    async for event in await aresponses(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        input="请用一句话介绍Python编程语言",
        stream=True,
    ):
        if hasattr(event, 'type') and event.type == "response.output_text.delta":
            print(event.delta or "", end="")
    print()


# %% ===================================================================================================================
def litellm_response_with_retry_usage():
    """
    展示 LiteLLM response重试API - 同步
    responses_with_retries 在请求失败时自动重试，参数与 responses() 一致。
    :return:
    """
    print("===> litellm_response_with_retry_usage")

    res = responses_with_retries(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        input="请用一句话介绍Python编程语言",
        max_output_tokens=200,
        num_retries=3,
    )
    print("res.status:", res.status)
    for item in res.output:
        if hasattr(item, 'content') and item.content:
            for content_block in item.content:
                if hasattr(content_block, 'text'):
                    print("content:", content_block.text)


async def litellm_response_with_retry_usage_async():
    """
    展示 LiteLLM response重试API - 异步
    aresponses_with_retries 是 responses_with_retries 的异步版本。
    :return:
    """
    print("===> litellm_response_with_retry_usage_async")

    res = await aresponses_with_retries(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        input="请用一句话介绍Python编程语言",
        max_output_tokens=200,
        num_retries=3,
    )
    print("res.status:", res.status)
    for item in res.output:
        if hasattr(item, 'content') and item.content:
            for content_block in item.content:
                if hasattr(content_block, 'text'):
                    print("content:", content_block.text)


# %% ===================================================================================================================
def litellm_completion_function_calling_usage():
    """
    展示 LiteLLM completion function calling 使用 - 同步
    Function Calling（工具调用）允许模型决定是否调用外部函数来获取信息。
    流程分为3步：
    1. 发送用户消息 + 工具定义给模型
    2. 模型返回 tool_calls（如果需要调用工具），执行工具并获取结果
    3. 将工具执行结果返回给模型，模型生成最终回复

    注意：Ollama 的 qwen2.5:7b 对 function calling 支持有限，可能不会触发工具调用。
    如果模型不支持原生 function calling，可以设置 litellm.add_function_to_prompt = True
    让 LiteLLM 将函数定义注入到 prompt 中。
    :return:
    """
    print("===> litellm_completion_function_calling_usage")

    # 检查模型是否支持 function calling
    print("supports_function_calling:", supports_function_calling(MODEL))
    print("supports_parallel_function_calling:", supports_parallel_function_calling(MODEL))

    # 定义工具（使用 OpenAI 的 tools 格式）
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "获取指定城市的当前天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "城市名称，例如：北京、上海",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "温度单位",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "执行数学计算",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，例如：2+2、10*5",
                        },
                    },
                    "required": ["expression"],
                },
            },
        },
    ]

    # 模拟的工具函数实现
    def get_current_weather(location: str, unit: str = "celsius") -> str:
        """模拟天气查询"""
        weather_data = {
            "北京": {"celsius": "5°C 晴天", "fahrenheit": "41°F 晴天"},
            "上海": {"celsius": "15°C 多云", "fahrenheit": "59°F 多云"},
        }
        return weather_data.get(location, {}).get(unit, f"{location} 天气数据暂不可用")

    def calculate(expression: str) -> str:
        """模拟计算器"""
        try:
            result = eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算出错: {e}"

    # 可用函数映射
    available_functions = {
        "get_current_weather": get_current_weather,
        "calculate": calculate,
    }

    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以查询天气和执行计算。"},
        {"role": "user", "content": "北京今天天气怎么样？顺便帮我算一下 123 * 456"},
    ]

    # Step 1: 发送请求，让模型决定是否需要调用工具
    print("--------- Step 1: 发送请求，模型决定是否调用工具 --------")
    res: ModelResponse = completion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto: 模型自行决定; none: 不调用; required: 必须调用
        # parallel_tool_calls=True,  # 是否允许并行调用多个工具（默认True）
    )
    print("res.choices[0].finish_reason:", res.choices[0].finish_reason)
    # 当 finish_reason 为 "tool_calls" 时，表示模型想要调用工具
    response_message = res.choices[0].message
    print("response_message.content:", response_message.content)  # 触发工具调用时 content 通常为 None
    print("response_message.tool_calls:", response_message.tool_calls)

    # Step 2: 检查是否有工具调用，如果有则执行
    tool_calls = response_message.tool_calls
    if tool_calls:
        print("\n--------- Step 2: 执行工具调用 --------")
        # 将模型的回复追加到消息历史中
        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"调用工具: {function_name}, 参数: {function_args}")

            # 执行对应的函数
            if function_name in available_functions:
                function_response = available_functions[function_name](**function_args)
            else:
                function_response = f"未知函数: {function_name}"

            print(f"工具返回: {function_response}")

            # 将工具执行结果追加到消息历史中
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": function_response,
            })

        # Step 3: 将工具结果发送回模型，获取最终回复
        print("\n--------- Step 3: 发送工具结果，获取最终回复 --------")
        final_res: ModelResponse = completion(
            base_url=LLM_URL,
            api_key=API_KEY,
            model=MODEL,
            messages=messages,
        )
        print("最终回复:", final_res.choices[0].message.content)
    else:
        # 模型没有触发工具调用，直接输出回复
        print("模型未触发工具调用，直接回复:", response_message.content)


async def litellm_completion_function_calling_usage_async():
    """
    展示 LiteLLM completion function calling 使用 - 异步
    异步版本的 function calling 流程与同步版本一致，只是使用 acompletion + await。
    :return:
    """
    print("===> litellm_completion_function_calling_usage_async")

    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "获取指定城市的当前天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "城市名称，例如：北京、上海",
                        },
                    },
                    "required": ["location"],
                },
            },
        },
    ]

    def get_current_weather(location: str) -> str:
        weather_data = {
            "北京": "5°C 晴天",
            "上海": "15°C 多云",
        }
        return weather_data.get(location, f"{location} 天气数据暂不可用")

    available_functions = {"get_current_weather": get_current_weather}

    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以查询天气。"},
        {"role": "user", "content": "上海今天天气怎么样？"},
    ]

    # Step 1: 异步请求
    res: ModelResponse = await acompletion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    response_message = res.choices[0].message
    print("finish_reason:", res.choices[0].finish_reason)
    print("tool_calls:", response_message.tool_calls)

    tool_calls = response_message.tool_calls
    if tool_calls:
        messages.append(response_message)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"调用工具: {function_name}, 参数: {function_args}")

            if function_name in available_functions:
                function_response = available_functions[function_name](**function_args)
            else:
                function_response = f"未知函数: {function_name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": function_response,
            })

        # Step 3: 异步获取最终回复
        final_res: ModelResponse = await acompletion(
            base_url=LLM_URL,
            api_key=API_KEY,
            model=MODEL,
            messages=messages,
        )
        print("最终回复:", final_res.choices[0].message.content)
    else:
        print("模型直接回复:", response_message.content)


# %% ===================================================================================================================
def litellm_embedding_usage():
    """
    LiteLLM embedding API使用 - 同步
    embedding() 用于将文本转换为向量表示（Embedding），常用于语义搜索、聚类等场景。
    返回格式：
    - data: 列表，每个元素包含 embedding（向量）和 index
    - model: 使用的模型名称
    - usage: token 使用量
    :return:
    """
    print("===> litellm_embedding_usage")

    # 单条文本 embedding
    print("--------- 单条文本 Embedding --------")
    res = embedding(
        model=MODEL_EMBEDDING,
        input=["如何使用Ollama获取Embeddings?"],
        api_base=LLM_URL,
        api_key=API_KEY,
    )
    print("type(res):", type(res))
    # 返回的是 litellm.utils.EmbeddingResponse 对象
    print("res.model:", res.model)
    print("res.object:", res.object)
    print("res.usage:", res.usage)
    # data 是 embedding 结果列表
    print("len(res.data):", len(res.data))
    if res.data:
        print("res.data[0].index:", res.data[0].index)
        print("res.data[0].object:", res.data[0].object)
        embedding_vector = res.data[0]["embedding"]
        print("embedding 向量维度:", len(embedding_vector))
        print("embedding 前5个值:", embedding_vector[:5])

    # 批量文本 embedding
    print("\n--------- 批量文本 Embedding --------")
    texts = [
        "在本地使用RTX-5060-Ti运行Ollama模型",
        "如何使用Ollama获取Embeddings?",
        "Python是最好的编程语言",
    ]
    res_batch = embedding(
        model=MODEL_EMBEDDING,
        input=texts,
        api_base=LLM_URL,
        api_key=API_KEY,
    )
    print("批量 embedding 数量:", len(res_batch.data))
    for i, item in enumerate(res_batch.data):
        vec = item["embedding"]
        print(f"  文本[{i}]: 维度={len(vec)}, 前3个值={vec[:3]}")


async def litellm_embedding_usage_async():
    """
    展示 LiteLLM embedding API使用 - 异步
    aembedding() 是 embedding() 的异步版本。
    :return:
    """
    print("===> litellm_embedding_usage_async")

    # 异步单条 embedding
    print("--------- 异步 Embedding --------")
    res = await aembedding(
        model=MODEL_EMBEDDING,
        input=["异步获取文本Embedding"],
        api_base=LLM_URL,
        api_key=API_KEY,
    )
    print("res.model:", res.model)
    if res.data:
        print("embedding 向量维度:", len(res.data[0]["embedding"]))

    # 异步批量 embedding
    print("\n--------- 异步批量 Embedding --------")
    texts = ["文本A", "文本B", "文本C"]
    res_batch = await aembedding(
        model=MODEL_EMBEDDING,
        input=texts,
        api_base=LLM_URL,
        api_key=API_KEY,
    )
    print("批量 embedding 数量:", len(res_batch.data))



# %% ===================================================================================================================
def litellm_batch_completion_usage():
    """
    展示 LiteLLM completion批处理API - 只有同步API
    completion 批处理API有3类：
    - batch_completion: 多个completion请求同一个模型（多个不同的 messages 列表）
    - batch_completion_models: 一个completion请求不同的模型，返回最快的那一个
    - batch_completion_models_all_responses: 一个completion请求不同的模型，返回所有模型的响应
    :return:
    """
    print("===> litellm_batch_completion_usage")

    # --- 1. batch_completion: 多个消息列表 → 同一个模型 ---
    # 传入一个 messages 的列表，每个元素是一个完整的对话消息列表
    print("--------- 1. batch_completion: 多个请求 → 同一模型 --------")
    messages_list = [
        [{"role": "user", "content": "请用一句话介绍Python"}],
        [{"role": "user", "content": "请用一句话介绍JavaScript"}],
        [{"role": "user", "content": "请用一句话介绍Golang"}],
    ]
    responses_list = batch_completion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages_list,
    )
    print("type(responses_list):", type(responses_list))
    print("返回结果数量:", len(responses_list))
    for i, res in enumerate(responses_list):
        print(f"  结果[{i}]:", res.choices[0].message.content)

    # --- 2. batch_completion_models: 一个消息 → 多个模型，返回最快的 ---
    # 注意：这里需要多个不同的模型，由于我们只有本地 Ollama，这里演示概念
    print("\n--------- 2. batch_completion_models: 一个请求 → 多个模型（返回最快） --------")
    print("注意：需要多个不同的模型才能体现效果，这里使用同一个模型演示")
    # 实际使用时可以传入多个不同的模型，如 ["gpt-3.5-turbo", "claude-3", "ollama/qwen2.5:7b"]
    try:
        fastest_res = batch_completion_models(
            models=[MODEL, MODEL],  # 实际应使用不同模型
            messages=[{"role": "user", "content": "1+1等于几？"}],
            base_url=LLM_URL,
            api_key=API_KEY,
        )
        print("最快返回:", fastest_res.choices[0].message.content)
    except Exception as e:
        print(f"batch_completion_models 异常（可能因为模型重复）: {e}")

    # --- 3. batch_completion_models_all_responses: 一个消息 → 多个模型，返回所有 ---
    print("\n--------- 3. batch_completion_models_all_responses: 一个请求 → 多个模型（返回全部） --------")
    print("注意：需要多个不同的模型才能体现效果，这里使用同一个模型演示")
    try:
        all_responses = batch_completion_models_all_responses(
            models=[MODEL, MODEL],  # 实际应使用不同模型
            messages=[{"role": "user", "content": "1+1等于几？"}],
            base_url=LLM_URL,
            api_key=API_KEY,
        )
        print("返回结果数量:", len(all_responses))
        for i, res in enumerate(all_responses):
            print(f"  模型[{i}]回复:", res.choices[0].message.content)
    except Exception as e:
        print(f"batch_completion_models_all_responses 异常（可能因为模型重复）: {e}")


# %% ===================================================================================================================
def litellm_completion_structured_output_usage():
    """
    展示 LiteLLM completion结构化输出API - 同步
    结构化输出（JSON Mode）让模型返回符合指定格式的 JSON 数据。
    有两种方式：
    1. response_format={"type": "json_object"}：要求模型返回合法 JSON（需要在 prompt 中说明格式）
    2. response_format={"type": "json_schema", "json_schema": {...}}：指定 JSON Schema 约束输出

    注意：Ollama 对 json_schema 的支持取决于模型版本，qwen2.5:7b 支持 json_object 模式。
    可以先检查模型是否支持 response_schema：
    - supports_response_schema(model, custom_llm_provider) 返回 True/False
    :return:
    """
    print("===> litellm_completion_structured_output_usage")

    # 检查模型对结构化输出的支持情况
    print("supports_response_schema:", supports_response_schema(MODEL, custom_llm_provider="ollama"))

    # --- 方式1: json_object 模式 ---
    # 需要在 prompt 中明确告诉模型输出 JSON 格式
    print("\n--------- 方式1: json_object 模式 --------")
    messages = [
        {"role": "system", "content": "你是一个JSON输出助手，请始终以JSON格式回复。"},
        {"role": "user", "content": "请列出3种编程语言及其主要用途，以JSON格式输出，格式为：[{\"name\": \"语言名\", \"usage\": \"用途\"}]"},
    ]
    res = completion(
        base_url=LLM_URL,
        api_key=API_KEY,
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"},
    )
    print("res.choices[0].message.content:")
    print(res.choices[0].message.content)
    # 尝试解析 JSON
    try:
        parsed = json.loads(res.choices[0].message.content)
        print("解析成功，类型:", type(parsed).__name__)
        print("解析结果:", parsed)
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")

    # --- 方式2: json_schema 模式（需要模型支持） ---
    print("\n--------- 方式2: json_schema 模式 --------")
    # 定义 JSON Schema
    json_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "programming_languages",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "languages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "编程语言名称"},
                                "usage": {"type": "string", "description": "主要用途"},
                                "rank": {"type": "integer", "description": "排名"},
                            },
                            "required": ["name", "usage", "rank"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["languages"],
                "additionalProperties": False,
            },
        },
    }
    try:
        res_schema = completion(
            base_url=LLM_URL,
            api_key=API_KEY,
            model=MODEL,
            messages=[
                {"role": "user", "content": "请列出3种编程语言及其主要用途和排名"},
            ],
            response_format=json_schema,
        )
        print("res_schema.choices[0].message.content:")
        print(res_schema.choices[0].message.content)
    except Exception as e:
        print(f"json_schema 模式可能不被当前模型支持: {e}")


# %% ===================================================================================================================
def litellm_completion_thinking_usage():
    """
    展示 LiteLLM completion thinking/reasoning 配置
    Thinking（推理）功能允许模型在生成最终回答之前进行内部推理。
    主要参数：
    - reasoning_effort: 推理力度，可选 "low"、"medium"、"high"（仅部分模型支持）
    - 对于 Anthropic 模型，还可以使用 thinking={"type": "enabled", "budget_tokens": 1024}

    响应中可获取：
    - response.choices[0].message.reasoning_content: 推理内容（字符串）
    - response.choices[0].message.thinking_blocks: 推理块列表（仅 Anthropic 模型）

    注意：Ollama 的 qwen2.5:7b 不原生支持 reasoning_effort 参数，
    但 qwen3 系列模型支持 thinking 模式。如果模型不支持，LiteLLM 会忽略该参数。
    可以通过 litellm.supports_reasoning(model) 检查模型是否支持推理功能。
    :return:
    """
    print("===> litellm_completion_thinking_usage")

    # 检查模型是否支持 reasoning
    from litellm import supports_reasoning
    print("supports_reasoning:", supports_reasoning(MODEL))

    messages = [
        {"role": "user", "content": "一个房间里有3个人，5个人离开，然后又来了2个人，现在房间里有几个人？请逐步推理。"},
    ]

    # 尝试使用 reasoning_effort 参数
    # 对于不支持的模型，可以设置 drop_params=True 来忽略不支持的参数
    print("\n--------- 尝试 reasoning_effort 参数 --------")
    try:
        res = completion(
            base_url=LLM_URL,
            api_key=API_KEY,
            model=MODEL,
            messages=messages,
            reasoning_effort="low",  # 推理力度：low/medium/high
            # drop_params=True,  # 如果模型不支持，自动丢弃该参数
        )
        print("res.choices[0].finish_reason:", res.choices[0].finish_reason)
        # 检查是否有 reasoning_content
        reasoning = res.choices[0].message.reasoning_content
        if reasoning:
            print("reasoning_content:", reasoning)
        else:
            print("（模型未返回 reasoning_content，可能不支持推理模式）")
        print("content:", res.choices[0].message.content)
    except Exception as e:
        print(f"reasoning_effort 不被当前模型支持: {e}")

    # 对于 Anthropic 模型，可以使用 thinking 参数
    print("\n--------- thinking 参数说明（适用于 Anthropic 模型） --------")
    print("""
    # Anthropic 模型的 thinking 参数用法：
    res = completion(
        model="anthropic/claude-3-7-sonnet-20250219",
        messages=[{"role": "user", "content": "..."}],
        thinking={"type": "enabled", "budget_tokens": 1024},
    )
    # 获取推理内容
    print(res.choices[0].message.reasoning_content)
    print(res.choices[0].message.thinking_blocks)  # 仅 Anthropic 返回
    """)

    # 使用 drop_params 安全地传递 reasoning_effort
    print("--------- 使用 drop_params=True 安全传递 --------")
    try:
        res = completion(
            base_url=LLM_URL,
            api_key=API_KEY,
            model=MODEL,
            messages=[{"role": "user", "content": "1+1等于几？"}],
            reasoning_effort="low",
            drop_params=True,  # 模型不支持时自动丢弃，不会报错
        )
        print("正常返回:", res.choices[0].message.content)
    except Exception as e:
        print(f"仍然出错: {e}")


# %% ===================================================================================================================
def main():
    litellm_completion_basic_usage()
    asyncio.run(litellm_completion_basic_usage_async())

    litellm_completion_with_retry_usage()
    asyncio.run(litellm_completion_with_retry_usage_async())

    litellm_response_usage()
    asyncio.run(litellm_response_usage_async())

    litellm_response_with_retry_usage()
    asyncio.run(litellm_response_with_retry_usage_async())

    litellm_completion_function_calling_usage()
    asyncio.run(litellm_completion_function_calling_usage_async())

    litellm_batch_completion_usage()
    litellm_completion_structured_output_usage()
    litellm_completion_thinking_usage()


if __name__ == "__main__":
    main()
