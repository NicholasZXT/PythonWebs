[TOC]

官方文档 [Model Context Protocol](https://modelcontextprotocol.io/docs/getting-started/intro).

# MCP架构

参考官方文档 [Architecture Overview](https://modelcontextprotocol.io/docs/learn/architecture).

## MCP角色

- MCP Host: 通常是AI应用，它可以创建持有多个MCP Client
- MCP Client: MCP通信的客户端，
- MCP Server: MCP服务提供方，用于给LLM提供上下文环境

## MCP体系

MCP包含了两层：

**Data Layer**: 数据层。
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


**Transport Layer**: 传输层。
- 定义了客户端-服务器之间的通信channel以及authentication。
- 目前有两种channel：
  - *Stdio transport*: 本地机器上，通过stdin和stdout进行通信。
  - *Streamable HTTP transport*: 跨机器的远程通信。

---
## 服务端

官方文档 [Server Concepts](https://modelcontextprotocol.io/docs/learn/server-concepts).

服务端的能力主要是3类服务原语。

### Tools

对应的就是 Function Calling 功能。

| Method       | Purpose                  | Returns                                |
| ------------ | ------------------------ | -------------------------------------- |
| `tools/list` | Discover available tools | Array of tool definitions with schemas |
| `tools/call` | Execute a specific tool  | Tool execution result                  |

### Resources

对应的就是 LLM 的上下文数据，比如文件、数据库等用于描述上下文的内容。

| Method                     | Purpose                         | Returns                                |
| -------------------------- | ------------------------------- | -------------------------------------- |
| `resources/list`           | List available direct resources | Array of resource descriptors          |
| `resources/templates/list` | Discover resource templates     | Array of resource template definitions |
| `resources/read`           | Retrieve resource contents      | Resource data with metadata            |
| `resources/subscribe`      | Monitor resource changes        | Subscription confirmation              |


### Prompts

| Method         | Purpose                    | Returns                               |
| -------------- | -------------------------- | ------------------------------------- |
| `prompts/list` | Discover available prompts | Array of prompt descriptors           |
| `prompts/get`  | Retrieve prompt details    | Full prompt definition with arguments |


---
## 客户端

官方文档 [Client Concepts](https://modelcontextprotocol.io/docs/learn/client-concepts).

客户端主要定义了如下3类能力。

### Sampling

Sampling指的是，MCP服务端在提供服务之前，可能需要借助MCP客户端向LLM发起请求（因为客户端是由AI应用程序发起的，所以客户端可以访问LLM），进行某些规划。
这个访问LLM的过程以及LLM返回的消息，MCP客户端都会进行提示，请求用户的准许（Human-in-the-loop control）。

### Elicitation

> 中文含义：“获取，引出，唤起”

Elicitation 指的是，MCP服务端在提供服务之前，可能需要借助MCP客户端向用户获取某些信息，比如用户输入的参数，或者用户选择的工具。

### Roots

Roots 指的是 MCP服务器可以访问的文件系统边界。

---

# MCP Python SDK

Github地址 [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk).

MCP Python 服务端是基于 starlette 开发的。

MCP Python package 源码里重要的有如下几部分：

---
## `types.py`

此文件里基于pydantic-v2定义了 MCP 服务端和客户端的JSON-RPC协议格式，
详细格式参见官方文档 [MCP Specification](https://modelcontextprotocol.io/specification/2025-06-18)）。

---
## `server` Module

模块 `server` 主要定义了 MCP 服务端的实现组件，分为如下几个子模块：

- `session.py`: 定义了服务端的 `ServerSession` 类。

- `stdio.py`: 定义了基于Stdio的服务端实现 `stdio_server` 函数。

### `fastmcp`
定义了 MCP 服务端的主要组件。

- `server.py`: 定义了 `FastMCP`类和`Context`类。


### `auth`
定义了 OAuth2 认证相关的类。

### `lowlevel`


---
## `client` Module

模块 `client` 主要定义了 MCP 客户端的实现组件。

- `session.py` 里定义了`ClientSession`。
- `session_group.py`
- `stdio`模块（其实只有一个`__init__.py`源码文件）定义了`stdio_client`的实现，以及`StdioServerParameters`。
- `sse.py` 里定义了`sse_client`的实现。
- `streamable_http.py` 里定义了`streamablehttp_client`的实现。
- `auth.py` 里定义了 OAuth2 认证相关的类。


## Example

MCP Python SDK 的官方文档目前写的并不完善，不过好在官方的仓库里提供了一些示例代码，存放在 `examples` 目录下，可以参考。

该目录下的内容如下：

### `snippets`

提供了一些 MCP 服务端/客户端开发示例代码，快速入门可以参考这里的示例 —— **推荐优先看这里的示例**。

- `clients`
- `servers`

### `fastmcp`

提供了一些基于 `FastMCP` 类进行MCP服务器开发的示例，比较有用。


### `clients`

提供了 MCP 客户端的示例代码。

主要有两个：
- `simple-auth-client`
- `simple-chatbot`

### `servers`

提供了基于更加底层的 `Server` + `ServerSession` 类进行MCP服务器开发的示例。

