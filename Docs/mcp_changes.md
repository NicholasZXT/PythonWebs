# MCP 与 FastMCP：版本变迁与迁移要点

> 整理日期：2026-09-23。所有版本与依赖约束数据均取自 PyPI 实测元数据，会随时间变化，复用前建议重新核对。

**第一部分 — MCP Python SDK v1 → v2**
依据：[What's new in v2](https://py.sdk.modelcontextprotocol.io/whats-new/) · [Migration Guide: v1 to v2](https://py.sdk.modelcontextprotocol.io/migration/) · [PyPI: mcp](https://pypi.org/project/mcp/#history)

**第二部分 — FastMCP v2 → v4**
依据：[What's New in FastMCP 4](https://gofastmcp.com/getting-started/whats-new) · [Upgrading from FastMCP 2](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2) · [Upgrading from FastMCP 3](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3) · [PyPI: fastmcp](https://pypi.org/project/fastmcp/#history)

---

# 第一部分：MCP Python SDK v1 → v2

## 一、v2 的本质：两条变更线叠加

v2 不是普通的版本递进，而是**两件独立的事同时发生**：

1. **SDK 自身重建** —— 客户端与服务端换用新的 dispatcher 引擎，引入一等公民 `Client`，并做了一批"首次导入即报错"的重命名。
2. **协议实现对齐 2026-07-28 修订版** —— 移除连接握手、会话，以及**所有服务端发起的请求**；同时对 2025 版老客户端保持兼容。

理解这一点很重要：前者是"改代码"，后者是"改架构"，两类问题的排查方式完全不同。

**v1.x 现状**：官方称进入维护期，仅收关键修复与安全补丁。但实测 v1 仍在发布 minor 版本（1.29.0 / 1.29.1 / 1.30.0，且与 v2 同日发布），说明它是一条并行活跃的开发线，而非冻结维护线。

## 二、主要 Breaking Changes

### 1. 入口层：导入路径与命名

| v1 | v2 | 报错症状 |
|---|---|---|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` | `ModuleNotFoundError: mcp.server.fastmcp` |
| `FastMCPError` | `MCPServerError` | `ImportError` |
| `McpError` | `MCPError` | `ImportError: cannot import name 'McpError'` |
| `ctx.fastmcp` | `ctx.mcp_server` | `AttributeError` |
| `mcp.get_context()` | 声明 `ctx: Context` 参数 | `AttributeError` |
| `import httpx` | `import httpx2` | `ModuleNotFoundError: No module named 'httpx'` |
| `streamablehttp_client` | 移除（残留拼写不再支持） | `ImportError` |
| `mcp.shared.version` | `mcp.types.version` | `ModuleNotFoundError` |
| `mcp.server.fastmcp.*` | `mcp.server.mcpserver.*` | `ModuleNotFoundError` |

注意 `mcp.server.fastmcp.*` 是**被删除而非弃用**，没有过渡期。但装饰器写法本身不变（`@mcp.tool()` / `@mcp.resource()` / `@mcp.prompt()` 语义一致），纯装饰器项目迁移量很小。

### 2. 依赖变化

| 依赖 | v1.28.1 | v2 | 说明 |
|---|---|---|---|
| httpx / httpx-sse | 必需 | **移除** | 被 httpx2 取代 |
| httpx2 | — | **新增必需** | `httpx.AsyncClient` → `httpx2.AsyncClient`，需审计 `except httpx.` 子句 |
| opentelemetry-api | — | **新增必需** | OTel 默认作为中间件开启 |
| mcp-types | — | **新增，精确锁定版本** | 与 mcp 版本必须严格一致，无版本弹性 |
| sse-starlette | `>=1.6.1` | `>=3.0.0` | 跨两个大版本 |

**TLS 校验改用 `truststore` 走操作系统信任库**（不再用 `certifi`），极简容器或私有 CA 环境可能握手失败。

### 3. 类型与线格式

- **属性全部改为 snake_case**：`inputSchema → input_schema`、`isError → is_error`、`nextCursor → next_cursor`、`mimeType → mime_type`、`structuredContent → structured_content`、`serverInfo → server_info`、`protocolVersion → protocol_version`、`uriTemplate → uri_template`、`listChanged → list_changed`、`progressToken → progress_token`。
  - **线上 JSON 仍是 camelCase**；构造时仍接受 camelCase 关键字参数，但**属性访问必须用 snake_case**。
  - 自行序列化要传 `model_dump(by_alias=True, mode="json")`。
- 协议类型移入独立发行包 **`mcp-types`**。若依赖 `mcp`，`import mcp.types` 是**永久别名**，无需改动。
- **资源 URI 由 `AnyUrl` 改为 `str`**（`Resource.uri`、`read_resource()`、subscribe/unsubscribe 等）。
- **消息联合类型不再是 `RootModel`**：`ClientRequest`、`ServerRequest`、`JSONRPCMessage` 等改为普通 union，校验改用 `client_request_adapter.validate_python(...)` 之类的 TypeAdapter，`.root` 访问失效。
- **额外字段不再保留**（v1 为 `extra="allow"`），自定义数据必须放进 `_meta`。
- 移除的类型别名：`Content → ContentBlock`、`ResourceReference → ResourceTemplateReference`、`Cursor → str`。
- `SUPPORTED_PROTOCOL_VERSIONS` 弃用，改用 `HANDSHAKE_PROTOCOL_VERSIONS` / `MODERN_PROTOCOL_VERSIONS`；`LATEST_PROTOCOL_VERSION` 值由 `2025-11-25` 变为 `2026-07-28`。

### 4. 高级服务端（MCPServer）

- **传输配置全部移出构造函数**：`MCPServer("x", port=9000)` 直接抛 `TypeError`。`host`、`port`、`sse_path`、`message_path`、`streamable_http_path`、`json_response`、`stateless_http`、`max_request_body_size`、`event_store`、`retry_interval`、`transport_security` 一律移入 `run()` / `sse_app()` / `streamable_http_app()`。
- `mount_path` 移除；挂载 ASGI app 改为把服务挂在某个前缀下。
- **不再读取 `MCP_*` 环境变量与 `.env`**（`Settings` 从 pydantic-settings 换成普通 Pydantic 模型）。
- `Context.client_id` 移除（改从 `meta` 或 OAuth token 获取）。
- 日志方法签名变为 `ctx.info({...})` / `ctx.log(level=..., data=...)`，`extra` 参数移除。
- `ProgressContext` 与 `progress()` 移除，改用 `Context.report_progress(progress, total, message)`（绝对值，非增量）。
- `call_tool()` 返回 `CallToolResult`；`get_prompt()` / `read_resource()` 可能返回 `InputRequiredResult`，需 `isinstance` 收窄类型。
- 默认服务名由 `FastMCP` 变为 `mcp-server`；构造函数位置参数顺序变化，**建议全部用关键字参数**。

### 5. 低级 Server（改动最大，属"重建"而非"重命名"）

| 维度 | v1 | v2 |
|---|---|---|
| 注册方式 | `@server.list_tools()` 装饰器 | `Server("x", on_list_tools=..., on_call_tool=...)` 关键字参数 |
| 处理器签名 | `async def list_tools() -> list[types.Tool]` | `async def f(ctx: ServerRequestContext, params: PaginatedRequestParams \| None) -> ListToolsResult` |
| 返回值 | 返回裸 list/dict，SDK 自动包装 | 必须手建 `ListToolsResult` / `CallToolResult` 等完整结果类型 |
| 工具内异常 | 变成 `isError: true` 的工具结果 | **变成 JSON-RPC 协议错误**，需自行 try/except 返回 `is_error=True` |
| 上下文 | `server.request_context`（ContextVar） | 由 `ctx: ServerRequestContext` 参数显式传入 |
| 扩展点 | 重写私有 `_handle_*`、改 handler 字典 | `add_request_handler(...)` + `middleware` 列表 |

### 6. 协议层（2026-07-28 的结构性改动）

- **无握手、无会话**：2026 客户端不在连接时协商，而是每个请求在 `_meta` 携带协议版本、客户端信息与能力；唯一的发现调用 `server/discover` 是普通请求。Streamable HTTP 的 2026 路径**不再有 `Mcp-Session-Id`**，任意副本都可应答请求，对负载均衡更友好。
- **服务端不能再调用客户端**：push elicitation、sampling、`roots/list` 全部移除。在 2026 连接上调用 `ctx.elicit()` 或 `ctx.session.create_message()` 会抛 `NoBackChannelError`。替代方案是**工具返回问题**（`InputRequiredResult`），由客户端回调应答后重试。
- **roots、sampling、协议级日志弃用**（SEP-2577，触发 `MCPDeprecationWarning`）；**`ping` 严格移除**。
- 通知合并为**单一长存流 `subscriptions/listen`**，取代独立的 HTTP GET 流与 `resources/subscribe`。
- 错误码标准化：资源不存在返回 `-32602`；新增 `-32020`（头不匹配）、`-32021`（缺失必填能力）、`-32022`（不支持的协议版本）。

### 7. 彻底移除

- **WebSocket 传输**（两端）及 `mcp[ws]` extra。
- **实验性 Tasks API**（`mcp.*.experimental`）。
- `mcp.shared.version`、`mcp.shared.progress`、`mcp.shared.session`。
- 废弃的 `streamablehttp_client` 拼写，以及 `streamable_http_client` 的 `get_session_id` 回调。

### 8. 值得关注的新特性

- **一等公民 `Client`**：v1 的"transport 上下文管理器 + `ClientSession` + 手动 `await session.initialize()`"三层嵌套，在 v2 合并为一个对象。`async with Client(url)` 即完成连接与版本协商，随后可直接读 `client.server_info` / `server_capabilities` / `protocol_version` / `instructions`。底层 `ClientSession` 仍可经 `client.session` 取得，但签名已随新引擎变化。
- **`Resolve(fn)` 参数注解**：工具参数由自写函数填充、对模型不可见，函数可返回 `Elicit(...)` 向用户提问。SDK 按连接机制自动选择传输方式（旧客户端走实时 elicitation，2026 走多轮往返）。这是中途获取客户端输入的推荐做法。

## 三、静默行为变更（导入不报错，最易踩）

官方专门单列这批变化——它们在导入期完全无感，往往到运行期才暴露：

1. **同步 `def` 处理器改由 worker 线程执行**（`anyio.to_thread.run_sync`）。不再阻塞事件循环，但线程亲和代码会炸——`asyncio.get_running_loop()` 在 `def` 里抛 `RuntimeError`。需留在事件循环就显式写 `async def`。
2. **工具内抛 `MCPError` 现在是协议错误，模型看不到**。其余异常仍变 `is_error=True` 结果，但**只有 `ToolError` 的消息传给模型**，其他异常只显示 `Error executing tool <name>`，堆栈进服务器日志。
3. **结果在离开前被校验**：手建的 `Tool` 若 `input_schema` 为 `{}` 会导致 `tools/list` 失败（规范要求 `"type": "object"`）。
4. **客户端会校验服务端应答**，不合规的服务器会让客户端抛 `pydantic.ValidationError`。
5. **URI 模板变成真正的 RFC 6570**，支持 `{+path}`、`{?query}`，改为精确匹配且默认拒绝路径遍历；严格模板在装饰时即失败。
6. **Streamable HTTP 的 lifespan 只在启动时运行一次**，状态被所有会话与请求共享（v1 是每会话/每无状态请求各跑一次）——原来靠 lifespan 存每会话状态的写法会串数据。
7. `mcp dev` / `mcp install` 生成的环境**固定到当前 SDK 版本**（原来解析最新稳定版）。

## 四、迁移执行顺序与注意点

**推荐顺序**：锁版本 → 导入与类名 → 字段 snake_case → 传输配置 → 运行时行为复查。

1. **先锁依赖区间**。若你发布的库依赖 `mcp` 而下游未就绪，写 `mcp>=1.28,<2`。同时审计 `except httpx.` 子句与 `sse-starlette` 下限。
2. **测试代码特别注意 `mode`**。`Client(...)` 默认与 v2 服务端协商 2026-07-28，因此**所有调用 `ctx.elicit()` 的既有测试都会在 v2 失败**。改法二选一：工具改用 `Resolve(...)` 参数，或测试客户端设 `Client(..., mode="legacy")`。服务端日志里出现 `server/discover` 请求属正常现象，不是 bug。
3. **横向扩展部署必须配置 `RequestStateSecurity(keys=[...])`**。2026 路径无会话、请求可被任意副本处理，多轮重试依赖跨 worker 传递密封的 `request_state`，而默认密钥**按进程生成**——不配共享密钥，多轮往返在负载均衡下会失效。
4. **`MCPError` 构造签名变了**：`McpError(ErrorData(...))` → `MCPError(code, message, data)`，或 `MCPError.from_error_data(error_data)`。
5. **`ElicitationResult` 不能用于 `isinstance()`**（它是 `TypeAliasType`，会抛 `TypeError`），要检查成员类如 `AcceptedElicitation`。
6. **资源未找到的异常类型变了**：`ResourceManager.get_resource()` 抛 `ResourceNotFoundError`，不再是 `ValueError`。
7. 不要手写 camelCase 序列化——`model_dump()` 输出 snake_case，`by_alias=True` 才是 wire 格式。

> 第 2、3 条（测试 `mode`、跨 worker 密钥）最容易在开发环境验证通过、却在上线后暴露——本地单进程、单副本场景下二者都不会报错。

## 五、升级时机建议（基于实测数据）

### 发布节奏

| 版本 | 日期 | 距 2.0.0 |
|---|---|---|
| 2.0.0a1 → rc1 | 2026-06-11 → 07-27 | 预发布期约 7 周 |
| **2.0.0** | **2026-07-28** | 0 天 |
| 2.1.0 / 2.1.1 | 08-24 / 08-25 | 27 / 28 天 |
| 2.0.1（回溯补丁） | 08-26 | 29 天 |
| **2.2.0（当前最新）** | **2026-09-07** | 41 天 |

v2 至今 11 个版本号（含 3a / 2b / 1rc），稳定版 5 个；稳定后约**每 10 天一个版本号且主要是 minor**，说明仍在引入新行为。

### 生态上界（决定性因素）

| 包 | 最新版（日期） | `mcp` 约束 |
|---|---|---|
| langchain-mcp-adapters | 0.3.2 (08-06) | `mcp<2.0.0,>=1.24.0` |
| mcp-use | 1.7.1 (09-10) | `mcp<2.0.0,>=1.24.0` |
| google-adk | 2.9.2 (09-18) | `mcp<2,>=1.24` |
| mcp-server-git / -fetch / -time | 2026.8.18 | `mcp<2,>=1.29.0` |
| strands-agents | 1.57.0 (09-22) | `mcp<2.2,>=1.23.0` |
| openai-agents | 0.22.3 (09-17) | `mcp<3,>=1.19.0` |
| fastmcp | 4.0.5 (09-17) | 无 mcp 依赖（独立实现协议） |

要点：**官方自己的参考服务器**在 2.0.0 发布三周后仍锁 `mcp<2`；主流集成层（LangChain、Google ADK）至今硬锁 `<2`；已出现渐进放宽迹象（strands-agents 放宽到 `<2.2`），但"约束允许"不等于"代码已适配"。

### 分场景结论

| 场景 | 建议 |
|---|---|
| 依赖第三方集成库 | **保持 v1**，写 `mcp>=1.30,<2`。依赖求解器会直接挡住 v2，这不是保守选择 |
| 新建、自包含项目 | **可直接上 2.2.0**——5 个稳定版 + 7 周 soak，且无迁移成本 |
| 存量生产服务 | **主线 v1.30 + CI 加 v2 实验 job**，等生态放开再切 |

**触发升级的信号**：① 所依赖的第三方库放开 `<2`；② v2 出现连续 4–6 周只有 patch、不出 minor 的稳定窗口；③ 确实需要 2026-07-28 协议特性（无会话带来的负载均衡友好、`subscriptions/listen` 单流、结果缓存提示 `ttlMs` / `cacheScope`、扩展机制）；④ 官方参考服务器自身迁移到 v2。

### 零成本预迁移清单

不管何时迁，这些改动在 v1 上做也无损，能显著降低未来成本：

1. 只用装饰器，不用 low-level `Server`（后者是被重建的，改动最大）。
2. 不依赖 `get_context()`，改为显式声明 `ctx: Context` 参数。
3. 减少直接读写 camelCase 属性，把字段访问收敛到少数位置。
4. 不使用 `ctx.elicit()` / sampling / roots（v2 已移除或弃用）。
5. 不使用 WebSocket 传输（v2 已移除）。
6. 同步 `def` 工具不要假设在事件循环线程。
7. 传输配置集中在一处，便于整体搬到 `run()`。
8. 版本约束显式写上界：`mcp>=1.30,<2`。

---

# 第二部分：FastMCP v2 → v4

## 一、先厘清依存关系（这是全部决策的前提）

`fastmcp` 4.x 已经是 `fastmcp-slim`（精确锁定版本）的薄封装，**真实依赖在 slim 包中**。逐版本核对 `requires_dist` 后得到：

| 版本 | 对官方 SDK 的约束 | 所属世界 |
|---|---|---|
| `fastmcp 2.14.7` | `mcp>=1.24.0,<2.0` | mcp 1.x |
| `fastmcp 3.0.0` | `mcp>=1.24.0,<2.0` | mcp 1.x |
| `fastmcp-slim 3.4.7` | `mcp>=1.24.0,<2.0`（client/mcp/server extra） | mcp 1.x |
| `fastmcp 4.0.5` | `mcp>=2.0.0,<3.0.0`，且核心依赖 `mcp-types>=2.0.0,<3.0.0` | mcp 2.x |

两条结论：

1. **FastMCP 4 构建在官方 MCP SDK v2 之上，不是独立实现协议。**
2. **分界线精确落在 v3 与 v4 之间。** v3 全线仍属 mcp 1.x 世界，与官方 SDK v1.30.0、`langchain-mcp-adapters`、`google-adk` 处于同一约束区间，可在同一环境共存；**v4 与它们互斥**——同一个 Python 环境既装 `mcp 1.x` 又装 `fastmcp 4` 会直接依赖解析失败。

这一点直接决定了迁移路径的选择，见第七节。

## 二、变更构成：两段叠加

v2 → v4 跨越两个大版本，需同时吸收 v3.0.0 / v2.14.0 / v2.13.0 的变更与 v4 的变更。官方迁移指南中标注 **Removed in v4** 的条目，是 v3 期弃用、**v4 才真正删除**的。

## 三、v3 阶段的主要 Breaking Changes

### 构造与配置

| 变更 | v2 | v3+ |
|---|---|---|
| 传输配置移出构造函数 | `FastMCP("s", host=..., port=...)` | 移入 `run()` / `run_http_async()` / `http_app()`；传旧参数抛 `TypeError` |
| 重复组件策略 | `on_duplicate_tools` / `on_duplicate_resources` / `on_duplicate_prompts` | 合并为单一 `on_duplicate=` |
| 标签过滤 | `include_tags` / `exclude_tags` | `server.enable(tags=..., only=True)` / `server.disable(tags=...)` |
| 工具序列化 | `tool_serializer=` | 从工具返回 `ToolResult` |
| 工具变换 | `tool_transformations=` | `server.add_transform(ToolTransform(...))` |

### API 重命名与签名

| 变更 | 说明 |
|---|---|
| `get_tools()` → `list_tools()` | 同类还有 resources / prompts / resource_templates；**返回值由 `dict` 改为 `list`** |
| `mcp.types.PromptMessage` → `fastmcp.prompts.Message` | **不再接受裸 dict 返回值** |
| `ctx.set_state()` / `ctx.get_state()` → **`async`** | 非序列化状态需 `serializable=False` |
| `tool.disable()` → `server.disable(names=..., components=...)` | 组件上直接调用抛 `NotImplementedError` |
| `WSTransport` → `StreamableHttpTransport` | WebSocket 客户端传输移除 |
| `meta` 键 `_fastmcp` → `fastmcp` | `include_fastmcp_meta` 参数移除 |
| `FASTMCP_SHOW_CLI_BANNER` → `FASTMCP_SHOW_SERVER_BANNER` | 环境变量改名 |
| OpenAPI `timeout=` 移除 | 改在 `httpx2.AsyncClient` 上配置 |
| 装饰器返回**原函数** | v2 返回 `FunctionTool`；v3 起可直接调用被装饰函数 |
| `FASTMCP_SERVER_AUTH_*` 自动加载移除 | 必须显式传参 |

### 安全相关（最该重视）

- **OAuth 存储后端 `DiskStore` → `FileTreeStore`，修复 CVE-2025-69872**。该修复**落在 v3.0.0，不在任何 v2.x**。显式传 `DiskStore` 需 `pip install 'py-key-value-aio[disk]'`，但会重新引入漏洞包。
- **OAuth Proxy 改为自签 JWT**（v2.13.0 起），生产环境必须显式提供 `jwt_signing_key` 与 `client_storage`，否则多副本部署的 token 校验会失效。
- v2.14 移除的弃用项：`BearerAuthProvider` → `JWTVerifier`；`Context.get_http_request()` → 依赖注入；`from fastmcp import Image` → `fastmcp.utilities.types`；`FastMCP(dependencies=[...])` → `fastmcp.json`；`FastMCPProxy(client=...)` → `client_factory`；`output_schema=False` → `None`。

### 其他

- 挂载的子服务拥有**隔离的 state store**，跨服务共享需显式传同一个 `session_state_store`。
- 后台任务需可选依赖 `pip install "fastmcp[tasks]"`。
- 仓库由 `jlowin/fastmcp` 迁至 `PrefectHQ/fastmcp`，写死旧地址的安装源需更新。

## 四、v4 阶段的主要 Breaking Changes

### 1. 依赖下限（最容易卡住安装）

`pydantic>=2.12`（锁 `2.11.*` 直接安装失败）、`Starlette>=1.0.1`、`FastAPI>=0.133.0`（首个支持 Starlette 1.x 的版本，FastAPI < 0.133.0 会因 Starlette 约束**无法解析依赖**）。在 FastAPI 内挂载 FastMCP 不受影响（已验证 FastAPI 0.135.2 + Starlette 1.3.1）。

### 2. httpx → httpx2（全栈）

自定义 `httpx_client_factory` 或 `httpx.Auth` 必须换成 httpx2。**最隐蔽的一点：`except httpx.ConnectError` 围绕 FastMCP 调用会变成死代码**，静态检查发现不了。日志名 `httpx`/`httpcore.*` → `httpx2`/`httpcore2.*`。

### 3. `McpError` 构造方式

```python
# v3 及以前
raise McpError(ErrorData(code=-32000, message="Client not supported"))
# v4
raise McpError(code=-32000, message="Client not supported")
```
捕获方式与 `err.error.code` 不变。

### 4. 导入路径迁移（摘主要项）

| 移除 | 替换 |
|---|---|
| `fastmcp.server.proxy` | `fastmcp.server.providers.proxy` |
| `fastmcp.server.openapi` / `FastMCPOpenAPI` | `FastMCP` + `OpenAPIProvider`（from `fastmcp.server.providers.openapi`） |
| `fastmcp.server.apps` / `fastmcp.server.app` | `fastmcp.apps` / `fastmcp` |
| `Tool` / `ToolResult` from `fastmcp.tools.tool` | `fastmcp.tools` |
| `Resource` from `fastmcp.resources.resource` | `fastmcp.resources` |
| `Prompt` / `Message` from `fastmcp.prompts.prompt` | `fastmcp.prompts` |
| `require_scopes` / `require_roles` / `restrict_tag` from `...auth.authorization` | `fastmcp.server.auth` |
| `TaskConfig` from `fastmcp.server.tasks` | `fastmcp.utilities.tasks` |
| `CurrentDocket` / `CurrentWorker` from `fastmcp.dependencies` | `fastmcp_tasks.dependencies` |

**无别名重命名**（旧名直接 `ImportError`）：`CachableToolResult` → `CacheableToolResult`；`PromptToolMiddleware` / `ResourceToolMiddleware` → `PromptsAsTools` / `ResourcesAsTools` transforms。

### 5. 服务器方法移除

| 移除 | 替换 |
|---|---|
| `FastMCP.as_proxy(sub)` | `create_proxy(sub)`（注意 `backend=` → `target=`） |
| `mcp.import_server(sub)` | `mcp.mount(sub)`（**语义不同**：静态快照 → 实时组合） |
| `mcp.mount(sub, prefix="x")` | `mcp.mount(sub, namespace="x")` |
| `mcp.mount(sub, as_proxy=True)` | 先 `create_proxy(sub)` 包裹再 `mount` |
| `mcp.add_tool_transformation(name, cfg)` | `mcp.add_transform(ToolTransform({name: cfg}))` |
| `mcp.remove_tool(name)` | `mcp.local_provider.remove_tool(name)`（抛 `KeyError`） |

### 6. 移除的参数

Tool 的 `serializer=`（→ 返回 `ToolResult`）与 `exclude_args=`（→ `Depends(factory)` 注入）；`decorator_mode` 与 `FASTMCP_DECORATOR_MODE=object`；`StreamableHttpTransport(sse_read_timeout=...)`。**`ctx.elicit()` 现需 `response_type`**：`await ctx.elicit("Approve?", response_type=bool)`。

### 7. 协议方向变化（架构级，兼容层无法掩盖）

- **`ctx.sample()`、`ctx.sample_step()`、`ctx.list_roots()` 从所有协议时代移除**——官方明确这是为了让不兼容代码在升级时**立即失败**而非静默出错。`FastMCP(sampling_handler=...)` 参数一并移除。
- **`ctx.elicit()` 在 2026-07-28 连接上抛 `ToolError`**（无会话时代没有回通道），握手时代仍可用。
- **后台任务移出核心规范**为 `io.modelcontextprotocol/tasks` 扩展（SEP-2663）：`task=True` 工具**必须注册 `TasksExtension` 否则启动抛 `RuntimeError`**；`task=` 仅限 tool 装饰器；客户端 `call_tool(..., task=True)` 抛 `TypeError`，改用 `call_tool`（自动轮询）或 `call_tool_task`。
- **资源模板默认启用路径安全筛查**，拒绝 `..` / 绝对路径 / 空字节；用 `ResourceSecurity(exempt_params={...})` 豁免。
- 资源未找到错误码 `-32002` → `-32602`；`ctx.set_state` 跨调用不持久；`client.ping()` 现代协议抛 `Method not found`；`Middleware.on_initialize` 不运行。
- 原始会话对象（`client.session` / `ctx.session` / `ctx.request_context`）现在是 SDK v2 对象，FastMCP 不包装。
- `Client("server.py")` 字符串推断 stdio **开始告警**，v5 移除，改用 `Client(Path("server.py"))`。

### 8. FastMCP 4 自动吸收的部分（无需改代码，但需知情）

- **camelCase 兼容桥**：导入时安装，旧 camelCase 属性仍可读但发 `FastMCPDeprecationWarning`。可用 `FASTMCP_MCP_CAMELCASE_COMPAT=false` 关闭。
- `fastmcp.types` 只含 FastMCP 自身类型，不再重导出协议类型（用 `mcp.types` 或 `mcp_types`）。

## 五、v4 主要新特性

| 特性 | 要点 |
|---|---|
| 双协议时代共存 | 一个部署同时服务现代与握手时代客户端，按连接协商；`Client(url)` 默认探测现代协议并回退 |
| 交互式工具 | 返回 `InputRequiredResult` 多轮往返，读 `ctx.input_responses` |
| `UserSession` / `SessionId` | 服务端会话状态绑定认证用户，像 `Context` 一样注入，不出现在 tool schema |
| 后台任务 | `TasksExtension` + Docket，支持 Redis / Valkey 持久化后端 |
| 扩展机制 | `mcp.add_extension()` / `Client(extensions=...)`，反向 DNS 标识 |
| 参数补全 | `@mcp.completion` 处理器 |
| 企业身份断言 | `IdentityAssertion` + `OAuthProxy`（beta，API 可能在 minor 变更） |
| 响应缓存 | `cache_ttl` / `cache_scope`，`KeyValueResponseCacheStore` 可放 Redis |
| `ClientGroup` | 多服务器单一工具目录，`{server}_{tool}` 命名空间，各成员独立协商协议版本 |
| 网关路由头 | 方法 / 目标名 / 参数值作为 HTTP 头，网关无需解析 JSON-RPC 包体 |
| 认证增强 | `require_roles`、`InsufficientScopeError`、`ClientCredentialsOAuthProvider` |

## 六、迁移注意点（按风险重排）

1. **先解决依赖，否则后面都免谈**：升 pydantic ≥ 2.12、FastAPI ≥ 0.133.0，常有连锁冲突，建议在独立分支先跑通依赖求解。
2. **处理两类"看不见"的失效**：① grep 所有 `except httpx.` —— 围绕 FastMCP 调用的会变成死分支；② **在 CI 里关闭 camelCase 兼容桥**（`FASTMCP_MCP_CAMELCASE_COMPAT=false`），本地跑通不代表迁移完成。
3. **处理被移除的回调能力**（最需要设计改动）：
   - `ctx.sample()` / `ctx.list_roots()`：服务器拥有模型就直接调用 LLM；需借用调用方模型则返回携带 sampling 请求的 `InputRequiredResult`。
   - `ctx.elicit()`：改写为 guard tool、按 `protocol_version` 分支，或 `Client(..., mode="legacy")`。
   - 后台任务：注册 `TasksExtension()`，去掉 resource / prompt 上的 `task=`。
4. **机械替换**：按第四节的表格逐项过（移动导入 → `as_proxy`→`create_proxy`、`import_server`→`mount`、`prefix=`→`namespace=` → 去掉废弃参数 → `McpError` 改关键字构造）。
5. **验证行为变化**：路径安全筛查、中间件现在看到**所有**入站消息（含通知与校验失败请求）、错误码 `-32602`、OAuth `issuer_url ≠ base_url` 会导致客户端**一次性重新授权**。
6. **路径建议**：官方称 "most FastMCP 3 servers upgrade unchanged"，但 **v2 不是 v3**。v2 → v4 跨越的弃用项太多，建议先在 v3 上跑一遍收集弃用警告，修完再上 v4。

## 七、升级时机与路径（基于实测数据）

### 版本线现状

| 版本线 | 末次发布 | 停更时长 |
|---|---|---|
| v2.x | 2.14.7（2026-04-13） | **163 天** |
| v3.x | 3.4.7（2026-08-10） | **44 天** |
| v4.x | 4.0.5（2026-09-17） | GA 至今 23 天 |

v4 发布节奏：a1(07-21) → a2(07-24) → b1(07-28) → b2(08-07) → b3(08-14) → b4(08-26) → b5(08-28) → **4.0.0 GA（08-31）** → 4.0.1 / 4.0.2(09-02) → 4.0.3(09-05) → 4.0.4(09-16) → 4.0.5(09-17)。
**约 6 周预发布 soak（7 个预发布版本），GA 后 5 个版本全是 patch、无 minor** —— 对比官方 SDK v2（每 10 天一个 minor），稳定信号更强。

### 与第一部分结论的差异

| 维度 | 官方 MCP SDK | FastMCP |
|---|---|---|
| 旧线状态 | v1.x 仍在发 minor（1.30.0，09-07） | v2.x 停更 163 天；连 v3.x 也停更 44 天 |
| 新版节奏 | 10 天一个 minor | GA 后全是 patch |
| 生态上界 | 主流库硬锁 `mcp<2` | 自身即入口，但该上界会传导进来 |

因此**两部分的策略方向相反**：官方 SDK 建议再等等；FastMCP 建议尽快离开 v2。

### 核心结论

> **若你决定官方 SDK 留在 v1（第一部分的建议），那么 FastMCP 的上限就是 v3.4.7 —— 这是目前与 v1 世界兼容的、且唯一修复了 CVE-2025-69872 的版本。**

### 分场景建议

| 你的情况 | 建议 |
|---|---|
| 与官方 SDK v1 同环境，或用到 `mcp<2` 的生态库 | **v2 → v3.4.7**。这是唯一可行且安全的落点 |
| 用到 OAuth（服务端或客户端） | **必须离开 v2.14.7**：该 CVE 在 v2 线无修复且永不会有补丁 |
| 完全自包含、不用官方 SDK v1、不用 OAuth、仅研究用途 | 可停在 2.14.7 等将来一步跳 v4；也可直接上 v4 体验新特性 |
| 需要 2026-07-28 协议特性（无会话、交互式工具、后台任务扩展） | 只能 v4，且必须接受与 v1 世界切割 |

**注意 v3.4.7 是终点站而非中转站**：它自身也已停更，不会再收到任何更新；但与 v4 之间的变更已冻结，你可以从容规划下一步。

### 实操路径

1. 先确认当前是否已是 2.14.7（v2 线内末版）；若更早，先原地升到 2.14.7，成本最低。
2. 在独立分支做 v2 → v3.4.7，重点处理：`list_tools()` 返回 list、`Message` 类替代裸 dict、`ctx.set_state/get_state` 改 async、传输参数移出构造函数、Auth Provider 显式传参。
3. 收集 v3 的弃用警告，形成清单 —— 这就是将来 v3 → v4 的待办。
4. 设立观察点：v4 连续 4–6 周只有 patch，或所依赖的生态库放开 `mcp<2`，再规划 v3 → v4。
