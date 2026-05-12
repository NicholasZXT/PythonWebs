# 目录

[TOC]

# 仓库

OpenTelemetry Python项目由两个主要 GitHub 仓库组成：

| 仓库                                                         | 作用                                                | 包前缀                                                       |
| ------------------------------------------------------------ | --------------------------------------------------- | ------------------------------------------------------------ |
| [`open-telemetry/opentelemetry-python`](https://github.com/open-telemetry/opentelemetry-python) | 核心规范实现（API + SDK）                           | `opentelemetry-api`,<br />`opentelemetry-sdk`                |
| [`open-telemetry/opentelemetry-python-contrib`](https://github.com/open-telemetry/opentelemetry-python-contrib) | 社区贡献插件（Instrumentation + Exporter + Distro） | `opentelemetry-instrumentation-*`,<br />`opentelemetry-exporter-*`,<br />`opentelemetry-distro-*` |



------

## 主要包

（1）API 层：`opentelemetry-api`

- 作用：定义抽象接口（`Tracer`, `Meter`, `Logger`）
- 特点：
  - 零依赖、轻量（< 100KB）
  - 默认 No-op 实现（无 SDK 时不产生数据）
- 使用场景：第三方库集成 OTel 时仅依赖此包

（2）SDK 层：`opentelemetry-sdk`

- 作用：API 的运行时实现，包含采样、Span 管理、资源模型等
- 关键子模块：
  - `opentelemetry.sdk.trace`：追踪实现
  - `opentelemetry.sdk.metrics`：指标实现
  - `opentelemetry.sdk.logs`：日志实现（实验性）
- 使用场景：应用主程序必须安装

（3）Exporter

- 位置：`opentelemetry-python-contrib` 仓库
- 命名规则：`opentelemetry-exporter-<backend>`
- 常见 Exporter：
  - `opentelemetry-exporter-otlp`：标准 OTLP 协议（推荐）
  - `opentelemetry-exporter-jaeger`：Jaeger 后端
  - `opentelemetry-exporter-prometheus`：Prometheus 指标
  - `opentelemetry-exporter-console`：控制台输出（调试用）

（4）Collector（收集器）

- Python 应用通过 Exporter（如 OTLP Exporter）将数据发送给 Collector
- Collector 本身以 Docker 容器或二进制形式部署

注意：**OpenTelemetry Collector 是独立的 Go 服务**，**不是 Python 包**！

（4）总结

| 功能       | 官方包                            | 来源仓库 | 对应 OTel 组件          | 仪表化方式       |
| ---------- | --------------------------------- | -------- | ----------------------- | ---------------- |
| API 接口   | `opentelemetry-api`               | core     | API                     | 手动 / 库        |
| SDK 实现   | `opentelemetry-sdk`               | core     | SDK                     | 手动 / 自动 / 库 |
| 自动启动器 | `opentelemetry-distro`            | contrib  | Distro                  | 自动             |
| 框架插桩   | `opentelemetry-instrumentation-*` | contrib  | Library Instrumentation | 自动 / 库        |
| 数据导出   | `opentelemetry-exporter-*`        | contrib  | Exporter                | 所有方式         |
| Collector  | ❌（非 Python 包）                 | Go 项目  | Collector               | 外部服务         |



------

## 三种仪表化使用的包

### （1）手动仪表化

核心包：

- `opentelemetry-api`（必须）
- `opentelemetry-sdk`（运行时需要）

### （2）自动仪表化

核心包：

- `opentelemetry-distro`：提供 `opentelemetry-instrument` 命令行工具
- `opentelemetry-instrumentation-*`：各类框架的自动插桩包（来自 contrib）

特点：

- 完全控制 Span 生命周期和属性
- 适用于核心业务逻辑埋点

常见插桩框架（完整列表见：[opentelemetry-python-contrib/instrumentation](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation)）：

| 包名                                     | 支持的库/框架        |
| ---------------------------------------- | -------------------- |
| `opentelemetry-instrumentation-flask`    | Flask                |
| `opentelemetry-instrumentation-fastapi`  | FastAPI              |
| `opentelemetry-instrumentation-django`   | Django               |
| `opentelemetry-instrumentation-requests` | requests HTTP 客户端 |
| `opentelemetry-instrumentation-psycopg2` | PostgreSQL           |
| `opentelemetry-instrumentation-redis`    | Redis                |

使用方式：

```bash
# 安装自动插桩发行版
pip install opentelemetry-distro opentelemetry-exporter-otlp
# 一键启动（自动注入所有支持的 instrumentation）
opentelemetry-instrument \
  --traces_exporter console \
  --metrics_exporter console \
  python app.py
```

### （3）库仪表化（Library Instrumentation）

本质：

- 就是上述 `opentelemetry-instrumentation-*` 包
- 可**手动注册**（不使用 `opentelemetry-instrument` 命令）

适用场景：

- 无法使用自动命令行启动（如 AWS Lambda）
- 需要定制插桩行为（如过滤敏感路径）