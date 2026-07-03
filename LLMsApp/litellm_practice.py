"""
LiteLLM使用
"""
# %% ===================================================================================================================
from typing import List, Dict, Tuple
import os
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
    :return:
    """
    print("===> litellm_completion_with_retry_usage")


async def litellm_completion_with_retry_usage_async():
    """
    展示 LiteLLM completion 重试API - 异步
    :return:
    """
    print("===> litellm_completion_with_retry_usage_async")



# %% ===================================================================================================================
def litellm_response_usage():
    """
    LiteLLM response API使用 - 同步
    :return:
    """
    print("===> litellm_response_usage")


async def litellm_response_usage_async():
    """
    展示 LiteLLM response API使用 - 异步
    :return:
    """
    print("===> litellm_response_usage_async")


# %% ===================================================================================================================
def litellm_response_with_retry_usage():
    """
    展示 LiteLLM response重试API - 同步
    :return:
    """
    print("===> litellm_response_with_retry_usage")


async def litellm_response_with_retry_usage_async():
    """
    展示 LiteLLM response重试API - 异步
    :return:
    """
    print("===> litellm_response_with_retry_usage_async")


# %% ===================================================================================================================
def litellm_completion_function_calling_usage():
    """
    展示 LiteLLM completion function calling 使用 - 同步
    :return:
    """
    print("===> litellm_completion_function_calling_usage")


async def litellm_completion_function_calling_usage_async():
    """
    展示 LiteLLM completion function calling 使用 - 异步
    :return:
    """
    print("===> litellm_completion_function_calling_usage_async")


# %% ===================================================================================================================
def litellm_embedding_usage():
    """
    LiteLLM embedding API使用 - 同步
    :return:
    """
    print("===> litellm_embedding_usage")


async def litellm_embedding_usage_async():
    """
    展示 LiteLLM embedding API使用 - 异步
    :return:
    """
    print("===> litellm_embedding_usage_async")



# %% ===================================================================================================================
def litellm_batch_completion_usage():
    """
    展示 LiteLLM completion批处理API - 只有同步API
    completion 批处理API有3类：
    - batch_completion: 多个completion请求同一个模型
    - batch_completion_models: 一个completion请求不同的模型，返回最快的那一个
    - batch_completion_models_all_responses: 一个completion请求不同的模型，返回所有模型的响应
    :return:
    """
    print("===> litellm_batch_completion_usage")


# %% ===================================================================================================================
def litellm_completion_structured_output_usage():
    """
    展示 LiteLLM completion结构化输出API - 同步
    :return:
    """
    print("===> litellm_completion_structured_output_usage")


# %% ===================================================================================================================
def litellm_completion_thinking_usage():
    """
    展示 LiteLLM completion thinking 配置
    :return:
    """
    print("===> litellm_completion_thinking_usage")






# %% ===================================================================================================================
def main():
    # litellm_completion_basic_usage()
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
