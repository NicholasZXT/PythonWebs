# 目录

[TOC]

# 仓库

OpenTelemetry Python项目由两个主要 GitHub 仓库组成：

（1）[`open-telemetry/opentelemetry-python`](https://github.com/open-telemetry/opentelemetry-python)

- 作用：核心规范实现（API + SDK）
- 主要包名：
  - `opentelemetry-api` 
  - `opentelemetry-sdk`
  - `opentelemetry-proto`
  - `opentelemetry-proto-json`
  - `opentelemetry-semantic-conventions`


（2）[`open-telemetry/opentelemetry-python-contrib`](https://github.com/open-telemetry/opentelemetry-python-contrib)

- 作用：社区贡献插件（Distro + Instrumentation + Exporter）
- 常用包名：
  - `opentelemetry-distro`
  - `opentelemetry-instrumentation`
  - `opentelemetry-instrumentation-*`
  - `opentelemetry-exporter-*`

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
- 使用场景：应用主程序必须安装并注册组件，启用OTel可观测性功能

（3）Exporter

- 位置：`opentelemetry-python-contrib` 仓库
- 命名规则：`opentelemetry-exporter-<backend>`
- 常用 Exporter：
  - `opentelemetry-exporter-otlp`：标准 OTLP 协议（推荐）
  - `opentelemetry-exporter-jaeger`：Jaeger 后端
  - `opentelemetry-exporter-prometheus`：Prometheus 指标
  - `opentelemetry-exporter-console`：控制台输出（调试用）

（4）Collector（收集器）

- Python 应用通过 Exporter（如 OTLP Exporter）将数据发送给 Collector
- Collector服务本身以 Docker 容器或二进制形式部署

注意：**OpenTelemetry Collector 是独立的 Go 服务**，**不是 Python 包**！

（5）总结

| 功能        | 官方包                               | 来源仓库    | 对应 OTel 组件              | 仪表化方式       |
|-----------|-----------------------------------|---------|-------------------------|-------------|
| API 接口    | `opentelemetry-api`               | core    | API                     | 手动 / 库      |
| SDK 实现    | `opentelemetry-sdk`               | core    | SDK                     | 手动 / 自动 / 库 |
| 自动启动器     | `opentelemetry-distro`            | contrib | Distro                  | 自动          |
| 框架插桩      | `opentelemetry-instrumentation-*` | contrib | Library Instrumentation | 自动 / 库      |
| 数据导出      | `opentelemetry-exporter-*`        | contrib | Exporter                | 所有方式        |
| Collector | ❌（非 Python 包）                     | Go 项目   | Collector               | 外部服务        |



------

## 三种仪表化使用的包

### 手动仪表化

核心包：

- `opentelemetry-api`（必须）
- `opentelemetry-sdk`（运行时需要）

特点：

- 完全控制 Span 生命周期和属性
- 适用于核心业务逻辑埋点

### 自动仪表化

核心包：

- `opentelemetry-distro`：提供 `opentelemetry-instrument` 命令行工具
- `opentelemetry-instrumentation-*`：各类框架的自动插桩包（来自 contrib）

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

### 库仪表化（Library Instrumentation）

本质：

- 就是上述 `opentelemetry-instrumentation-*` 包
- 可**手动注册**（不使用 `opentelemetry-instrument` 命令）

示例（以Flask项目为例）：

```python
from flask import Flask
from opentelemetry.instrumentation.flask import FlaskInstrumentor

app = Flask(__name__)

# 手动启用 Flask 插桩
FlaskInstrumentor().instrument_app(app)
```

适用场景：

- 无法使用自动命令行启动（如 AWS Lambda）
- 需要定制插桩行为（如过滤敏感路径）


------------------------------------------------------------------------------------------------------

# `opentelemetry-api`

实际导入时的包名为`opentelemetry.xxx`，主要有如下模块。


## `metrics`

主要定义在`_internal`包里，有用内容如下：

一、`__init__.py`

- 定义了`MeterProvider`、`Meter`两个抽象类
- 定义了`class NoOpMeterProvider(MeterProvider)`、`class NoOpMeter(Meter)`两个默认实现
- 定义了3个工具函数：
  - `get_meter_provider`
  - `set_meter_provider`
  - `get_meter`


二、`instrument.py`

定义了各种指标的抽象基类与实现类。

（1）`class Instrument(ABC)`，所有指标工具的抽象基类，它下面又有异步和同步两个抽象子类：

- `class Synchronous(Instrument)`
- `class Asynchronous(Instrument)`

所有指标工具类都继承于这两个类，不过这两个类更多是起到区分标识作用，定义中没有差别。

（2）各类指标工具的同步/异步抽象基类。


## `trace`


------------------------------------------------------------------------------------------------------

# `opentelemetry-sdk`

实际导入时的包名为`opentelemetry.sdk.xxx`，主要有如下模块。

## `metrics`



## `trace`


------------------------------------------------------------------------------------------------------