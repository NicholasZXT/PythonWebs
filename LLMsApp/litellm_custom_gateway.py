"""
LiteLLM接入自定义网关服务示例
"""
# %%
import os
# 禁用远程 cost map 获取，避免网络警告
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from datetime import datetime
import uuid
import hashlib
from typing import Any, Iterator, Generator, AsyncIterator, AsyncGenerator
import litellm
from litellm import completion, acompletion, batch_completion
from litellm import ModelResponse
from litellm.types.utils import Choices, Message, Usage


# 跳过 SSL 证书验证
litellm.ssl_verify = False

# ============================================================
# 自定义 API 配置
# ============================================================
API_BASE = 'https://custom.gateway.com'
APP_KEY = 'sk-some-key'
APP_SECRET = 'sk-some-secret'
# MODEL_NAME = 'openai/deepseek-v4-flash'
MODEL_NAME = 'deepseek/deepseek-v4-flash'


# %%
def _generate_auth_headers() -> dict[str, str]:
    """生成自定义 API 网关所需的认证请求头（每次调用重新签名）"""
    current_time = int(datetime.now().timestamp())
    nonce = uuid.uuid4().hex
    signature = hashlib.sha256(
        f"{current_time}{APP_SECRET}{nonce}{current_time}".encode('utf-8')
    ).hexdigest().upper()

    return {
        'x-tif-apikey': APP_KEY,
        'x-tif-timestamp': str(current_time),
        'x-tif-nonce': nonce,
        'x-tif-signature': signature,
        'Content-Type': 'application/json',
    }


def _collect_stream_response(
    response: Iterator[ModelResponse],
    print_thinking: bool = False,
) -> tuple[ModelResponse, str, str]:
    """将流式响应收集为完整的 ModelResponse + content + thinking_content 三元组（用于非流式调用场景）"""
    collected_content = ""
    collected_reasoning = ""
    model_name = MODEL_NAME
    finish_reason = "stop"
    usage_info = None
    thinking_started = False
    content_started = False

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            if print_thinking and not thinking_started:
                print("[thinking]: ", end='', flush=True)
                thinking_started = True
            collected_reasoning += delta.reasoning_content
            if print_thinking:
                print(delta.reasoning_content, end='', flush=True)
        if delta.content:
            if print_thinking and not content_started:
                if thinking_started:
                    print()  # thinking 结束后换行
                print("[content]: ", end='', flush=True)
                content_started = True
            collected_content += delta.content
            if print_thinking:
                print(delta.content, end='', flush=True)
        if chunk.choices[0].finish_reason:
            finish_reason = chunk.choices[0].finish_reason
        if hasattr(chunk, 'model') and chunk.model:
            model_name = chunk.model
        if hasattr(chunk, 'usage') and chunk.usage:
            usage_info = chunk.usage

    message = Message(role="assistant", content=collected_content)
    if collected_reasoning:
        message.reasoning_content = collected_reasoning

    choice = Choices(index=0, message=message, finish_reason=finish_reason)
    result = ModelResponse(
        id=str(uuid.uuid4()),
        choices=[choice],
        model=model_name,
        object="chat.completion",
    )
    if usage_info:
        result.usage = usage_info
    return result, collected_content, collected_reasoning


class StreamResponse:
    """同步流式响应包装器：可迭代获取 chunk，迭代完成后可通过 thinking_content 获取完整思维链内容"""

    def __init__(self, response: Iterator[ModelResponse], print_thinking: bool = False) -> None:
        self._iter = response
        self._print_thinking = print_thinking
        self.content: str = ""
        self.thinking_content: str = ""
        self._thinking_started: bool = False
        self._content_started: bool = False

    def __iter__(self) -> Generator[ModelResponse, None, None]:
        for chunk in self._iter:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    if self._print_thinking and not self._thinking_started:
                        print("[thinking]: ", end='', flush=True)
                        self._thinking_started = True
                    self.thinking_content += delta.reasoning_content
                    if self._print_thinking:
                        print(delta.reasoning_content, end='', flush=True)
                if delta.content:
                    if self._print_thinking and not self._content_started:
                        if self._thinking_started:
                            print()  # thinking 结束后换行
                        print("[content]: ", end='', flush=True)
                        self._content_started = True
                    self.content += delta.content
                    if self._print_thinking:
                        print(delta.content, end='', flush=True)
            yield chunk


class AsyncStreamResponse:
    """异步流式响应包装器：可异步迭代获取 chunk，迭代完成后可通过 thinking_content 获取完整思维链内容"""

    def __init__(self, response: AsyncIterator[ModelResponse], print_thinking: bool = False) -> None:
        self._iter = response
        self._print_thinking = print_thinking
        self.content: str = ""
        self.thinking_content: str = ""
        self._thinking_started: bool = False
        self._content_started: bool = False

    async def __aiter__(self) -> AsyncGenerator[ModelResponse, None]:
        async for chunk in self._iter:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    if self._print_thinking and not self._thinking_started:
                        print("[thinking]: ", end='', flush=True)
                        self._thinking_started = True
                    self.thinking_content += delta.reasoning_content
                    if self._print_thinking:
                        print(delta.reasoning_content, end='', flush=True)
                if delta.content:
                    if self._print_thinking and not self._content_started:
                        if self._thinking_started:
                            print()  # thinking 结束后换行
                        print("[content]: ", end='', flush=True)
                        self._content_started = True
                    self.content += delta.content
                    if self._print_thinking:
                        print(delta.content, end='', flush=True)
            yield chunk


def custom_completion(
    messages: list[dict[str, str]],
    stream: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str = "high",
    enable_thinking: bool = True,
    print_thinking: bool = False,
    **kwargs: Any,
) -> tuple[ModelResponse, str, str] | StreamResponse:
    """
    使用 litellm 调用 DeepSeek-v4，自动附加自定义网关认证头。

    Args:
        messages:         消息列表 [{"role": "user", "content": "..."}]
        stream:           是否流式返回
        temperature:      温度参数
        max_tokens:       最大 token 数
        reasoning_effort: 推理力度，可选 "high" / "medium" / "low"
        enable_thinking:  是否开启思维链（thinking）
        print_thinking:   是否在控制台实时打印 thinking 内容（默认 False）
        **kwargs:         传递给 litellm.completion 的其他参数

    Returns:
        stream=False: tuple[ModelResponse, str, str] — (模型响应, content文本, thinking文本)
        stream=True:  StreamResponse 迭代器，迭代完成后通过 .content / .thinking_content 获取文本
    """
    extra_headers = _generate_auth_headers()

    # reasoning_effort 和 thinking 通过 extra_body 传入：
    # 自定义 API 网关的模型不在 litellm 已知参数白名单中，直接传参会被litellm 校验拒绝；
    # extra_body 会原样合并到请求体，不经校验。
    extra_body: dict[str, Any] = {}
    if reasoning_effort:
        extra_body['reasoning_effort'] = reasoning_effort
    if enable_thinking:
        extra_body['thinking'] = {"type": "enabled"}

    # vLLM 后端始终返回 SSE 格式，必须用 stream=True 请求
    response = completion(
        model=MODEL_NAME,
        api_base=API_BASE,
        api_key="Empty",
        messages=messages,
        stream=True,                    # 强制流式，兼容 vLLM SSE 响应
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers=extra_headers,
        extra_body=extra_body,
        **kwargs
    )

    if stream:
        return StreamResponse(response, print_thinking=print_thinking)
    else:
        return _collect_stream_response(response, print_thinking=print_thinking)


async def custom_acompletion(
    messages: list[dict[str, str]],
    stream: bool = False,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str = "high",
    enable_thinking: bool = True,
    print_thinking: bool = False,
    **kwargs: Any,
) -> tuple[ModelResponse, str, str] | AsyncStreamResponse:
    """
    异步版 custom_completion，参数相同。

    Returns:
        stream=False: tuple[ModelResponse, str, str] — (模型响应, content文本, thinking文本)
        stream=True:  AsyncStreamResponse 异步迭代器，迭代完成后通过 .content / .thinking_content 获取文本
    """
    extra_headers = _generate_auth_headers()

    # reasoning_effort 和 thinking 通过 extra_body 传入（避免 litellm 参数校验拒绝）
    extra_body: dict[str, Any] = {}
    if reasoning_effort:
        extra_body['reasoning_effort'] = reasoning_effort
    if enable_thinking:
        extra_body['thinking'] = {"type": "enabled"}

    # vLLM 后端始终返回 SSE 格式，必须用 stream=True 请求
    response = await acompletion(
        model=MODEL_NAME,
        api_base=API_BASE,
        api_key="Empty",
        messages=messages,
        stream=True,                    # 强制流式，兼容 vLLM SSE 响应
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers=extra_headers,
        extra_body=extra_body,
        **kwargs
    )

    if stream:
        return AsyncStreamResponse(response, print_thinking=print_thinking)
    else:
        return _collect_stream_response(response, print_thinking=print_thinking)


def custom_batch_completion(
    messages_list: list[list[dict[str, str]]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str = "high",
    enable_thinking: bool = True,
    print_thinking: bool = False,
    **kwargs: Any,
) -> list[tuple[ModelResponse, str, str]]:
    """
    批量调用 DeepSeek-v4，逐条发送并收集非流式结果。

    Args:
        messages_list:   消息列表的列表，每个元素是一组消息
                         例如: [[sys_msg, user_msg1], [sys_msg, user_msg2], ...]
        temperature:     温度参数
        max_tokens:      最大 token 数
        reasoning_effort: 推理力度
        enable_thinking:  是否开启思维链
        print_thinking:   是否在控制台实时打印 thinking 内容（默认 False）
        **kwargs:         传递给 litellm.completion 的其他参数

    Returns:
        list[tuple[ModelResponse, str, str]]: 每个请求的 (模型响应, content文本, thinking文本) 元组
    """
    extra_headers = _generate_auth_headers()

    # reasoning_effort 和 thinking 通过 extra_body 传入（避免 litellm 参数校验拒绝）
    extra_body: dict[str, Any] = {}
    if reasoning_effort:
        extra_body['reasoning_effort'] = reasoning_effort
    if enable_thinking:
        extra_body['thinking'] = {"type": "enabled"}

    # batch_completion 要求所有请求共享 headers/extra_body，但认证头有有效期，
    # 因此这里用 batch_completion 一次性发送，所有请求共用同一组签名头
    responses = batch_completion(
        model=MODEL_NAME,
        api_base=API_BASE,
        api_key="Empty",
        messages=messages_list,          # 传入 list[list]，一次批量发送
        stream=True,                     # 兼容 vLLM SSE 响应
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers=extra_headers,
        extra_body=extra_body,
        **kwargs
    )

    # batch_completion 返回 Generator[ModelResponse]，逐个收集为完整响应
    return [_collect_stream_response(resp, print_thinking=print_thinking) for resp in responses]

# %%
def main():
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请介绍下你最擅长的top-5编程语言"}
    ]

    # -------- 非流式：print_thinking=True 实时打印思维链，同时通过 tuple 返回 --------
    # _collect_stream_response 会自动打印 [thinking]: 和 [content]: 标签及内容
    print("=== 非流式调用（print_thinking=True）===")
    resp, content, thinking = custom_completion(
        test_messages, stream=False, print_thinking=True
    )
    print()
    print(f"[content 共 {len(content)} chars]")
    print(f"[thinking 共 {len(thinking)} chars]")

    # -------- 流式：print_thinking=True 实时打印，迭代完成后从 .thinking_content 取回 --------
    # StreamResponse 在 print_thinking=True 时会自动打印 [thinking]: 和 [content]: 标签
    print("\n=== 流式调用（print_thinking=True）===")
    stream_resp = custom_completion(
        test_messages, stream=True, print_thinking=True
    )
    for chunk in stream_resp:
        pass  # 标签和内容由 StreamResponse 自动打印
    print()
    print(f"[content 共 {len(stream_resp.content)} chars]")
    print(f"[thinking 共 {len(stream_resp.thinking_content)} chars]")

    # -------- 流式：print_thinking=False，仅静默累积 --------
    print("\n=== 流式调用（print_thinking=False，静默累积）===")
    stream_resp2 = custom_completion(
        test_messages, stream=True, print_thinking=False
    )
    for chunk in stream_resp2:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end='', flush=True)
    print()
    print(f"[content 共 {len(stream_resp2.content)} chars]")
    print(f"[thinking 共 {len(stream_resp2.thinking_content)} chars]")
    print(stream_resp2.thinking_content[:300])

    # -------- 批量：逐条收集 (ModelResponse, thinking) 元组 --------
    print("\n=== 批量调用 ===")
    batch_messages = [
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "用一句话介绍 Python"}
        ],
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "用一句话介绍 JavaScript"}
        ],
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "用一句话介绍 Go"}
        ],
    ]
    batch_results = custom_batch_completion(batch_messages, print_thinking=True)
    for i, (resp, content, thinking) in enumerate(batch_results):
        print(f"\n--- 第 {i+1} 条 ---")
        print(f"[content {len(content)} chars] {content[:200]}")
        print(f"[thinking {len(thinking)} chars] {thinking[:200]}")


if __name__ == '__main__':
    main()
