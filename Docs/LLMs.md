[TOC]


------
# LiteLLM

官方文档 [LiteLLM](https://docs.litellm.ai/).

## 介绍

### 定位

LiteLLM **不是一个全栈 LLM 应用框架**，而是一个**轻量级的 LLM API 统一封装层**（或称为“适配器”、“翻译器”）。

它的唯一使命是：

> **让开发者用一套 OpenAI 风格的 API 调用，无缝对接 100+ 家不同厂商的大语言模型服务。**

它不关心你的应用逻辑、数据处理、Agent 编排或 RAG 流程，只专注于解决“**如何调用模型**”这一底层问题。

### 特点

（1）**统一接口，兼容 OpenAI SDK**

- 所有调用都遵循 `openai.ChatCompletion.create()` 或 `client.chat.completions.create()` 的格式。
- 开发者只需学习 OpenAI 一种 API，即可调用所有支持的模型。

（2）**支持超 100+ 模型提供商**

（3）**两种使用方式**

- Python SDK：嵌入到应用代码中，作为函数库使用。
- Proxy Server（API 网关）：部署为独立服务，提供统一的 `/v1/chat/completions` 端点，后端可路由到多个模型，支持负载均衡、故障转移、密钥管理等企业级功能。

（4）**企业级能力**

- 成本追踪：自动计算每次调用的 token 消耗和费用。
- 预算控制：可设置项目/用户级别的花费上限。
- 可观测性：集成 Prometheus、Datadog、LangSmith 等日志与监控系统。
- 高可用：内置重试、超时、降级策略。

（5）**容易上手，入侵性极低**

- 几乎零学习成本，代码改动极小。
- 可与任何上层框架（如 LangChain、LlamaIndex、FastAPI、Flask）无缝集成。

------

## Python SDK

> LiteLLM官方只提供了Python SDK，没有提供其他语言的SDK。
>
> 看了下源码，**LiteLLM Python SDK并不是一个轻量级的包**，内容比我以为的要多不少。



------

## Proxy Server




------
# MCP

官方文档 [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro).

MCP 是一个**开源标准协议**，用于将 AI 应用连接到外部系统。可以把它理解为 **AI 应用的 "USB-C 接口"**——就像 USB-C 为电子设备提供统一连接标准一样，MCP 为 AI 应用提供了连接外部数据源、工具和工作流的统一标准。

**核心价值：**

- **开发者**：降低构建和集成 AI 应用的开发复杂度
- **AI 应用/Agent**：获得丰富的数据源、工具和应用生态
- **终端用户**：AI 应用能访问用户数据并代替用户执行操作

## MCP架构

参考官方文档 [Architecture Overview](https://modelcontextprotocol.io/docs/learn/architecture).

### MCP角色

MCP的三大参与者如下：

```text   
┌─────────────────────────────────────┐
│         MCP Host (AI 应用)          │
│  ┌─────────┐ ┌─────────┐           │
│  │Client 1 │ │Client 2 │ ┌────────┐│
│  └────┬────┘ └────┬────┘ │Client 3││
│       │           │      └───┬────┘│
└───────┼───────────┼──────────┼─────┘
        │           │          │
   ┌────▼────┐ ┌───▼────┐ ┌──▼──────┐
   │Server A │ │Server B│ │Server C │
   │(本地)    │ │(本地)   │ │(远程)    │
   └─────────┘ └────────┘ └─────────┘
```

| 参与者     | 定义                                           | 示例                            |
| ---------- | ---------------------------------------------- | ------------------------------- |
| MCP Host   | 协调管理多个 MCP Client 的 AI 应用             | Claude Desktop、VS Code、Cursor |
| MCP Client | 维护与一个 MCP Server 的连接组件               | Host 内部实例化的协议级对象     |
| MCP Server | 向 Client 提供上下文（数据/工具/提示词）的程序 | 文件系统服务器、Sentry 服务器   |



### MCP体系

MCP体系有两层：

| 层级                     | 职责                                 | 关键技术                                                     |
| ------------------------ | ------------------------------------ | ------------------------------------------------------------ |
| 数据层 (Data Layer)      | 定义 JSON-RPC 2.0 消息协议、核心原语 | `server/discover`、`tools/list`、`tools/call`                |
| 传输层 (Transport Layer) | 管理通信通道和认证                   | Stdio（本地进程通信）、Streamable HTTP（远程，支持 SSE 流式传输） |

**Data Layer**: 

- 定义了基于 JSON-RPC 的传输格式。
- Data Layer 层定义了如下3个功能：
  - Lifecycle management: MCP有状态通信的生命周期管理。
  - **Primitives**: 服务原语，也就是MCP Server提供的服务能力 —— 这是使用方最关注的。
  - Notifications: 服务端和客户端之间的通知机制。比如server端提供的工具列表有变动，client会收到通知。

其中服务原语分为服务端和客户端：
- 服务端有3类：
  - Tools, 
  - Resources, 
  - Prompts.
- 客户端有3类：
  - Sampling
  - Elicitation
  - Logging

**Transport Layer**: 传输层

- 定义了客户端-服务器之间的通信channel以及authentication。
- 目前有两种channel：
  - *Stdio transport*: 本地机器上，通过stdin和stdout进行通信。
  - *Streamable HTTP transport*: 跨机器的远程通信。

**无状态 & 发现机制**

- MCP 是**无状态协议**：每个请求都在 `_meta` 字段中携带协议版本、客户端能力和身份信息
- 通过 `server/discover` 请求实现能力发现（版本协商 + 能力声明）
- 发现结果可缓存，不需要每次请求都重复执行

---
### 服务端

官方文档 [Server Concepts](https://modelcontextprotocol.io/docs/learn/server-concepts).

服务端的能力主要是3类服务原语。

| 原语      | 本质         | 控制方 | 类比        |
| --------- | ------------ | ------ | ----------- |
| Tools     | 可执行的操作 | 🤖 模型 | API 函数    |
| Resources | 只读的数据   | 📄 应用 | 数据库/文件 |
| Prompts   | 交互模板     | 👤 用户 | 工作流模板  |


#### Tools — 由模型控制

可执行函数，对应的就是 Function Calling 功能，**AI 模型根据上下文自主决定何时调用**。

**控制方**：LLM 模型根据上下文自主决定调用时机，但应用层可实现用户审批机制（确认对话框、权限设置等）。

| Method       | Purpose      | Returns                                |
| ------------ | ------------ | -------------------------------------- |
| `tools/list` | 发现可用工具 | Array of tool definitions with schemas |
| `tools/call` | 执行指定工具 | Tool execution result                  |


#### Resources — 由应用控制

**只读数据源**，对应的就是 LLM 的上下文数据，比如文件、数据库等用于描述上下文的内容。

支持两种模式：

- **直接资源**：固定 URI，如 `calendar://events/2024`
- **资源模板**：动态 URI，如 `travel://activities/{city}/{category}`

**控制方**：应用决定何时获取、如何使用资源数据（embedding 检索、关键词搜索、直接传入模型）。

| Method                     | Purpose      | Returns                                |
| -------------------------- | ------------ | -------------------------------------- |
| `resources/list`           | 列出可用资源 | Array of resource descriptors          |
| `resources/templates/list` | 发现资源模板 | Array of resource template definitions |
| `resources/read`           | 读取资源内容 | Resource data with metadata            |
| `resources/subscribe`      | 监听资源变化 | Subscription confirmation              |

一、**Resource支持的资源类型**

MCP 协议层面不限制具体格式，通过数据载体和 `mimeType` 支持任意类型：

| 数据载体字段 | 数据类型      | 适用场景     | 示例                           |
| ------------ | ------------- | ------------ | ------------------------------ |
| `text`       | 字符串        | 文本类资源   | Markdown, JSON, 纯文本代码     |
| `blob`       | Base64 二进制 | 非文本类资源 | PDF, DOCX, PNG/JPEG 图像, 音频 |

**注意**：协议支持传输任何格式，但**实际能否被 LLM 消费，取决于 Client/Host 的实现**。例如：图像需要 Host 支持 Vision 能力；PDF 可能需要 Server 端先提取文本再作为 `text` 返回，而不是直接返回二进制。

二、**加载时机与机制**

核心结论：*Resources 不会像 Tools 那样自动注入 LLM 上下文*。

- Tools 的方式：启动时获取 schema -> 注入 LLM 上下文 -> LLM 自主决定调用（模型驱动）。
- Resources 的方式：启动时仅获取资源目录/索引 -> **资源内容不进入上下文** -> 应用层按需读取（应用驱动）。

三种具体的加载模式：

1. 预加载：对话开始前，应用主动加载关键资源（如启动时加载用户日历、偏好设置）。
2. 按需加载：应用根据对话上下文判断需要时，才读取资源（如用户问“我的日程”时才读取日历）。
3. 模型建议加载：LLM 分析后建议应用加载某资源（如 LLM 返回：“建议查看用户的日历资源来确认可用日期”）。



#### Prompts — 由用户控制

**可复用的交互模板**，指导模型如何组合使用工具和资源，封装经过验证的交互模式。

**控制方**：用户主动触发（斜杠命令 `/plan-vacation`、命令面板、UI 按钮）。

| Method         | Purpose        | Returns                               |
| -------------- | -------------- | ------------------------------------- |
| `prompts/list` | 发现可用提示词 | Array of prompt descriptors           |
| `prompts/get`  | 获取提示词详情 | Full prompt definition with arguments |

一、**支持的形态**

`arguments` 字段是可选的，因此支持两种形态：

- 带参数的模板：包含占位符，使用时传入参数由 Server 渲染（如 `/plan-vacation Barcelona 7`）。

```json
{
  "name": "plan-vacation",
  "title": "Plan a vacation",
  "arguments": [
    { "name": "destination", "type": "string", "required": true },
    { "name": "duration", "type": "number" }
  ]
}
```

- 纯提示词（无参数）：不包含占位符，直接返回固定的、经过精心设计的 messages 数组（如 `/code-review-checklist`）。

```json
{
  "name": "code-review-checklist",
  "title": "Code Review Checklist",
  "description": "Standard code review guidelines",
  "arguments": []  // 空参数
}
```

返回示例：

```json
{
  "messages": [
    {
      "role": "system",
      "content": {
        "type": "text",
        "text": "Please review the following code for:\n1. Security vulnerabilities\n2. Performance issues\n3. Code style compliance\n4. Test coverage"
      }
    }
  ]
}
```


二、**加载时机与触发机制（两阶段）**

核心结论：*Prompts 列表不会注入 LLM 上下文，内容仅在用户显式触发后加载*。

| 阶段         | 时机                    | 协议方法       | 作用与数据流向                                               |
| ------------ | ----------------------- | -------------- | ------------------------------------------------------------ |
| 阶段一：发现 | 应用启动 / 打开命令面板 | `prompts/list` | 返回轻量元数据（name, title, description）。仅停留在应用层用于渲染 UI（如斜杠命令列表），不消耗 LLM Token。 |
| 阶段二：激活 | 用户主动触发命令        | `prompts/get`  | 返回完整的 messages 数组。Host 将其注入当前对话上下文，LLM 才开始基于此进行推理。 |

三、**核心使用场景**

1. 标准化工作流模板：将复杂交互封装为一键命令（如 `/deploy-service`）。
2. 领域专家知识注入：固化特定领域的最佳实践（如 `/security-audit`）。
3. 多步骤任务引导：引导用户逐步提供信息，避免 LLM 遗漏关键参数。
4. 跨团队统一交互标准：不同 Server 暴露同名 Prompt，Host 统一呈现。
5. 降低使用门槛：用户无需手写复杂 Prompt，直接选择预定义命令。

四、**高阶用法：作为 Tool 的工作流编排指南**

可以将 Tool 的使用步骤封装为 Prompts，实现“编排逻辑”与“执行能力”的解耦——这正是官方推荐的用法之一。

- 写在 Tool description 中：LLM 始终可见，每次推理都消耗 Token，且多 Tool 协作逻辑分散。
- 封装为 Prompt：按需加载（省 Token），协作逻辑集中管理，支持参数化。
- 三位一体编排：在 Prompt 中同时指导 LLM 如何调用 **Tools** 并引用 **Resources** 中的数据。

五、**MCP Prompts vs Skills**

| 对比维度   | Agent Skills (框架级)                     | MCP Prompts (协议级)                                         |
| ---------- | ----------------------------------------- | ------------------------------------------------------------ |
| 元数据加载 | 启动时注入 LLM 上下文                     | 不进 LLM 上下文（仅加载到应用层 UI）                         |
| 触发机制   | LLM 自主判断触发 + 用户手动               | 仅用户显式触发                                               |
| Token 消耗 | 始终占用（即使本次对话未使用）            | 零消耗（直到被用户触发）                                     |
| 设计哲学   | 模型中心（Model-Centric）：优化模型自主性 | 用户中心（User-Centric）：优化用户控制力与 Token 效率        |
| 标准化程度 | 框架私有：跨框架不互通                    | 协议标准：一次编写，在 Claude/Cursor/VS Code 等任意 MCP Client 中通用 |



---
### 客户端

官方文档 [Client Concepts](https://modelcontextprotocol.io/docs/learn/client-concepts).

客户端主要定义了如下3类能力。

| 能力                    | 状态           | 说明                                                   |
| ----------------------- | -------------- | ------------------------------------------------------ |
| Elicitation（信息征询） | ✅ 最新版本保留 | Server 向用户请求额外信息（表单模式 / URL 模式）       |
| Roots（根目录）         | ⚠️ 已弃用       | 指定 Server 可访问的文件系统范围，建议改用工具参数     |
| Sampling（采样）        | ⚠️ 已弃用       | Server 通过 Client 请求 LLM 补全，建议直接集成 LLM API |


#### Elicitation

> 中文含义：“获取，引出，唤起”

Elicitation 指的是，MCP服务端在提供服务之前，可能需要借助MCP客户端向用户获取某些信息，比如用户输入的参数，或者用户选择的工具。

这是 Client 端最核心的**当前可用**能力，支持两种模式：

- **Form 模式**：Server 提供 JSON Schema，Client 渲染表单让用户填写
- **URL 模式**：Server 提供 URL，用户自行打开完成操作（适用于密码、OAuth 等敏感操作）

遵循 **MRTR（Multi Round-Trip Requests）** 模式：

```text
Client → Server: tools/call
Server → Client: InputRequiredResult（需要用户输入）
Client → User: 展示 UI
User → Client: 提供信息
Client → Server: 重试请求（附带用户输入）
Server → Client: 最终结果
```


#### Sampling (Deprecated)

Sampling指的是，MCP服务端在提供服务之前，可能需要借助MCP客户端向LLM发起请求（因为客户端是由AI应用程序发起的，所以客户端可以访问LLM），进行某些规划。
这个访问LLM的过程以及LLM返回的消息，MCP客户端都会进行提示，请求用户的准许（Human-in-the-loop control）。


#### Roots (Deprecated)

Roots 指的是 MCP服务器可以访问的文件系统边界。


---

## MCP Python SDK

Github地址 [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk).

MCP Python 服务端是基于 starlette 开发的。

MCP Python package 源码里重要的有如下几部分：

---
### `types.py`

此文件里基于pydantic-v2定义了 MCP 服务端和客户端的JSON-RPC协议格式，
详细格式参见官方文档 [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18)）。

---
### `server` Module

模块 `server` 主要定义了 MCP 服务端的实现组件，分为如下几个子模块：

- `session.py`: 定义了服务端的 `ServerSession` 类。

- `stdio.py`: 定义了基于Stdio的服务端实现 `stdio_server` 函数。

#### `fastmcp`
定义了 MCP 服务端的主要组件。

- `server.py`: 定义了 `FastMCP`类和`Context`类。


#### `auth`
定义了 OAuth2 认证相关的类。

#### `lowlevel`


---
### `client` Module

模块 `client` 主要定义了 MCP 客户端的实现组件。

- `session.py` 里定义了`ClientSession`。
- `session_group.py`
- `stdio`模块（其实只有一个`__init__.py`源码文件）定义了`stdio_client`的实现，以及`StdioServerParameters`。
- `sse.py` 里定义了`sse_client`的实现。
- `streamable_http.py` 里定义了`streamablehttp_client`的实现。
- `auth.py` 里定义了 OAuth2 认证相关的类。


### Example

MCP Python SDK 的官方文档目前写的并不完善，不过好在官方的仓库里提供了一些示例代码，存放在 `examples` 目录下，可以参考。

该目录下的内容如下：

#### `snippets`

提供了一些 MCP 服务端/客户端开发示例代码，快速入门可以参考这里的示例 —— **推荐优先看这里的示例**。

- `clients`
- `servers`

#### `fastmcp`

提供了一些基于 `FastMCP` 类进行MCP服务器开发的示例，比较有用。


#### `clients`

提供了 MCP 客户端的示例代码。

主要有两个：
- `simple-auth-client`
- `simple-chatbot`

#### `servers`

提供了基于更加底层的 `Server` + `ServerSession` 类进行MCP服务器开发的示例。



------

## FastMCP v2.0

官方文档 [FastMCP](https://gofastmcp.com/getting-started/welcome).

这是一个基于 MCP Python SDK 进行二次开发的 MCP package。

> 实际上，根据 FastMCP 官方文档的说法，FastMCP 的1.0版本被合并吸收到了 MCP Python SDK 中了。
> FastMCP v2.0 版本是一个全新的版本，也是基于 MCP Python SDK 构建的。
> 相关讨论可以参见 [FastMCP 2.0 vs MCP Python SDK Server #1068](https://github.com/modelcontextprotocol/python-sdk/issues/1068).
> 个人感觉，**FastMCP v2.0 的文档更加清晰，用起来更方便**。

FastMCP v2.0 源码结构如下；

### `settings.py`

基于 `pydantic_settings` 的 `BaseSettings` 类定义了 FastMCP 的配置参数类 `Settings`。

### `mcp_config.py`

基于 `pydantic` 的 `BaseModel` 类定义了 MCP 服务器的各种配置类：
- `StdioMCPServer`
- `RemoteMCPServer`
- `MCPConfig`: 汇总配置类


### `client` module


### `server` module


### `tools` module


### `resources` module


### `prompts` module


### `cli` module


### `utilities` module
