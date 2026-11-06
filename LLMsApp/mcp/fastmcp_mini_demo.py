"""FastMCP 最小示例：一个同时包含 Tools / Resources / Prompts 三类 Primitive 的 MCP Server。

本文件是**教学样例**，用最小的篇幅把 MCP 三大 Primitive 讲清楚，业务逻辑一律是内存打桩。

三类 Primitive 的分工（这是理解 MCP 的关键）：

+--------------+--------------------------------+----------------------------------+
| Primitive    | 由谁调用                       | 典型用途                         |
+==============+================================+==================================+
| **Tool**     | 模型自主决定调用               | 有副作用/有计算的「动作」，         |
|              |                                | 例如查询、下单、跑一段逻辑        |
+--------------+--------------------------------+----------------------------------+
| **Resource** | 客户端（宿主）读取，模型不主动调 | 只读的「上下文/数据」，            |
|              |                                | 例如配置文件、库表内容、文件      |
+--------------+--------------------------------+----------------------------------+
| **Prompt**   | 用户显式选择（斜杠命令、模板）   | 预置的「对话开场白」，              |
|              |                                | 用来引导模型进入某个工作流        |
+--------------+--------------------------------+----------------------------------+

运行::

    ./.venv/Scripts/python.exe mcps/fastmcp_server.py                     # 默认 stdio
    ./.venv/Scripts/python.exe mcps/fastmcp_server.py --transport http    # HTTP，默认 8000 端口

自测（列出三类 Primitive 并实际调用一遍）::

    ./.venv/Scripts/python.exe mcps/fastmcp_server.py --self-test
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from fastmcp.prompts import Message
from pydantic import Field

# ======================================================================================
# 1. 日志：stdio 传输下 stdout 是 JSON-RPC 协议通道，日志必须走 stderr
# ======================================================================================
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,  # 关键：绝不能写 stdout，否则会污染协议流
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
logger = logging.getLogger("fastmcp_server")


# ======================================================================================
# 2. 打桩数据：一个极简的「企业名录」
# ======================================================================================
_COMPANIES: dict[str, dict[str, Any]] = {
    "C001": {
        "id": "C001",
        "name": "常州星罗智能装备有限公司",
        "industry": "工业自动化",
        "city": "常州",
        "employees": 320,
        "revenue_2025": 18500.0,  # 单位：万元
        "tags": ["专精特新", "规上企业"],
    },
    "C002": {
        "id": "C002",
        "name": "苏州数场工业数据科技有限公司",
        "industry": "工业软件",
        "city": "苏州",
        "employees": 96,
        "revenue_2025": 4200.0,
        "tags": ["高新技术企业", "瞪羚企业"],
    },
    "C003": {
        "id": "C003",
        "name": "无锡恒力精密机械股份有限公司",
        "industry": "通用机械",
        "city": "无锡",
        "employees": 780,
        "revenue_2025": 41300.0,
        "tags": ["上市后备", "规上企业"],
    },
}


# ======================================================================================
# 3. 创建 Server
# ======================================================================================
# instructions 会随 initialize 握手返回给客户端，用于告诉模型「这个服务能干什么」。
mcp = FastMCP(
    name="fastmcp-minimal-demo",
    instructions=("企业名录示例服务。提供企业检索、企业详情读取，以及企业分析与对比的提示词模板。")
)


# ======================================================================================
# 4. Tools —— 模型可自主调用
# ======================================================================================
# 要点：
#   * 函数签名即 Schema：类型注解 + Field 描述会被自动转成 JSON Schema；
#   * docstring 就是工具描述，模型靠它判断该不该调用；
#   * 返回 dict / list / Pydantic 模型会被自动序列化并生成 outputSchema；
#   * 同步函数会自动放到线程池执行，不会阻塞事件循环。

@mcp.tool
def add(a: float, b: float) -> float:
    """把两个数字相加。用于验证服务连通性的最小工具。"""
    return a + b


@mcp.tool(name="search_companies", tags={"company"})
def search_companies(
    keyword: Annotated[str, Field(description="关键词，匹配企业名称或行业，为空则返回全部")] = "",
    limit: Annotated[int, Field(description="最多返回条数", ge=1, le=50)] = 5,
) -> list[dict[str, Any]]:
    """按关键词检索企业名录，返回精简字段列表。"""
    kw = keyword.strip()
    hits = [
        {
            "id": c["id"],
            "name": c["name"],
            "industry": c["industry"],
            "city": c["city"],
        }
        for c in _COMPANIES.values()
        if not kw or kw in c["name"] or kw in c["industry"]
    ]
    logger.info("search_companies keyword=%r -> %d 条", keyword, len(hits))
    return hits[:limit]


@mcp.tool(name="get_company_profile", tags={"company"})
async def get_company_profile(company_id: str) -> dict[str, Any]:
    """按企业 ID 读取完整画像。异步工具用于演示耗时 I/O 场景。"""
    await asyncio.sleep(0)  # 占位：真实场景这里是数据库/HTTP 调用
    company = _COMPANIES.get(company_id)
    if company is None:
        # 抛异常会让客户端收到 isError=true 的错误结果，模型可以据此纠正参数重试。
        raise ValueError(f"企业不存在：{company_id}（可选值：{', '.join(_COMPANIES)}）")
    return company


# ======================================================================================
# 5. Resources —— 客户端读取的只读上下文
# ======================================================================================
# 要点：
#   * uri 是资源的唯一标识（自定义 scheme，如 demo://、file://、db://）；
#   * 带 {} 的 uri 是**资源模板**，客户端传参后由函数形参接收；
#   * 返回 str 按 mime_type 原样下发；返回 dict/list 时 FastMCP 默认序列化为 JSON。

@mcp.resource("demo://server/info", name="服务信息", mime_type="application/json")
def server_info() -> dict[str, Any]:
    """读取本服务的元信息与数据概览。"""
    total_revenue = sum(c["revenue_2025"] for c in _COMPANIES.values())
    return {
        "server": "fastmcp-minimal-demo",
        "transport": "stdio / http",
        "company_count": len(_COMPANIES),
        "total_revenue_2025": round(total_revenue, 2),  # 万元
        "industries": sorted({c["industry"] for c in _COMPANIES.values()}),
    }


@mcp.resource("demo://companies/{company_id}", name="企业详情", mime_type="text/markdown")
def company_markdown(company_id: str) -> str:
    """把单个企业渲染成 Markdown 文本，便于直接作为上下文喂给模型。"""
    company = _COMPANIES.get(company_id)
    if company is None:
        return f"未找到企业 `{company_id}`。"
    tags = "、".join(company["tags"]) or "无"
    return (
        f"# {company['name']}\n\n"
        f"- 企业 ID：{company['id']}\n"
        f"- 所属行业：{company['industry']}\n"
        f"- 所在城市：{company['city']}\n"
        f"- 员工人数：{company['employees']} 人\n"
        f"- 2025 年营收：{company['revenue_2025']} 万元\n"
        f"- 企业标签：{tags}\n"
    )


# ======================================================================================
# 6. Prompts —— 用户显式选择的对话模板
# ======================================================================================
# 要点：
#   * 返回 str 时，FastMCP 会包装成一条 user 消息；
#   * 返回 list[Message] 时可精确控制 role / content，适合多轮或 few-shot；
#   * 带参数的 prompt 会在客户端渲染成「斜杠命令 + 参数表单」。

@mcp.prompt(name="analyze_company", tags={"analysis"})
def analyze_company(
    company_name: str,
    focus: Literal["综合", "财务", "产业链位置", "风险"] = "综合",
) -> str:
    """生成「单企业分析」的提示词。"""
    return (
        f"请围绕「{focus}」这个视角，对 **{company_name}** 做一份简要分析。\n\n"
        "要求：\n"
        "1. 先调用 search_companies 定位企业，再用 get_company_profile 拿到完整画像；\n"
        "2. 结论分点输出，每点不超过两句话；\n"
        "3. 数据缺失时明确写「数据不足」，不要编造。"
    )


@mcp.prompt(name="compare_companies", tags={"analysis"})
def compare_companies(company_a: str, company_b: str) -> list[Message]:
    """生成「双企业对比」的提示词（返回多角色消息，演示 Message 用法）。"""
    return [
        Message(
            role="user",
            content=(
                f"请对比 **{company_a}** 与 **{company_b}**，"
                "从营收规模、人员规模、行业归属三个维度列表对照，并给出一句结论。"
            ),
        ),
        Message(
            role="assistant",
            content="好的，我会先读取两家企业的画像数据，再按维度列表对照。",
        ),
        Message(
            role="user",
            content="另外请补充：如果只能选一家做产业链上下游合作，你会选哪家，为什么？",
        ),
    ]


# ======================================================================================
# 7. 入口
# ======================================================================================
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FastMCP 最小示例（Tools / Resources / Prompts）")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "http", "streamable-http", "sse"],
        help="传输方式，默认 stdio（FastMCP 4 起 http 即 streamable-http）",
    )
    parser.add_argument("--host", default="127.0.0.1", help="仅 http/sse 传输生效")
    parser.add_argument("--port", type=int, default=8000, help="仅 http/sse 传输生效")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="内存态自测：列出三类 Primitive 并逐一调用，不启动服务",
    )
    return parser.parse_args(argv)


async def _run_self_test() -> int:
    """不启动子进程，直接把三类 Primitive 列出来并调用一遍。"""
    from fastmcp import Client

    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        prompts = await client.list_prompts()

        print("=== Tools ===")
        for t in tools:
            print(f"  - {t.name}: {(t.description or '').splitlines()[0]}")

        print("=== Resources ===")
        for r in resources:
            print(f"  - {r.uri}")
        for rt in templates:
            print(f"  - {rt.uri_template}  (模板)")

        print("=== Prompts ===")
        for p in prompts:
            args = ", ".join(a.name for a in (p.arguments or []))
            print(f"  - {p.name}({args})")

        print("\n=== 调用结果 ===")
        print("add(1, 2) ->", (await client.call_tool("add", {"a": 1, "b": 2})).data)
        print("search_companies('工业') ->", json.dumps(
            (await client.call_tool("search_companies", {"keyword": "工业"})).data,
            ensure_ascii=False,
        ))
        print("get_company_profile('C001') ->", json.dumps(
            (await client.call_tool("get_company_profile", {"company_id": "C001"})).data,
            ensure_ascii=False,
        ))
        info = await client.read_resource("demo://server/info")
        print("read demo://server/info ->", info[0].text)
        md = await client.read_resource("demo://companies/C003")
        print("read demo://companies/C003 ->\n" + md[0].text)
        p1 = await client.get_prompt("analyze_company", {"company_name": "星罗智能", "focus": "财务"})
        print("prompt analyze_company ->", p1.messages[0].content.text)
        p2 = await client.get_prompt("compare_companies", {"company_a": "星罗", "company_b": "数场"})
        print(f"prompt compare_companies -> {len(p2.messages)} 条消息")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.self_test:
        return asyncio.run(_run_self_test())

    logger.info("启动 MCP Server：transport=%s", args.transport)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
