"""
OpenTelemetry实践练习

OTel 数据管道架构概览:
┌──────────────────────────────────────────────────────────────────────┐
│                         业务代码 (API 层)                             │
│  get_meter() → Counter/Gauge/Histogram    get_tracer() → Span        │
│  logging.getLogger() ← 桥接模式复用标准库                              │
└──────────────┬──────────────┬──────────────┬─────────────────────────┘
               │              │              │
               ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        SDK 配置层 (Provider)                          │
│  MeterProvider                  TracerProvider    LoggerProvider     │
│  ├─ Resource (标识数据来源)       ├─ Resource       ├─ Resource        │
│  ├─ MetricReader (拉取/推送)      ├─ Sampler        ├─ LogRecordLimits │
│  ├─ View (属性过滤/聚合策略)       ├─ SpanLimits     └─ LoggingHandler  │
│  └─ ExemplarFilter              └─ SpanProcessor                     │
└──────────────┬──────────────┬──────────────┬─────────────────────────┘
               │              │              │
               ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    处理管道 (Processor / Reader)                      │
│  PeriodicExportingMetricReader   SimpleSpanProcessor    Simple/Batch │
│  InMemoryMetricReader            BatchSpanProcessor     LogRecordProc│
└──────────────┬──────────────┬──────────────┬─────────────────────────┘
               │              │              │
               ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       导出层 (Exporter)                               │
│  ConsoleMetricExporter   ConsoleSpanExporter   ConsoleLogRecordExporter│
│  (开发) OTLPMetricExporter  OTLPSpanExporter   OTLPLogExporter (生产) │
└──────────────┬──────────────┬──────────────┬─────────────────────────┘
               │              │              │
               ▼              ▼              ▼
         [OTLP Collector] [Jaeger] [Prometheus] [云监控] ...
"""
from typing import Iterable, List, Set, Dict
import os
import platform
import socket
import time
import psutil
import logging
import atexit
from functools import lru_cache
# 下面这个属于 opentelemetry-semantic-conventions 包
from opentelemetry.semconv.schemas import Schemas
# %% --------------- 导入OpenTelemetry-API ---------------
# 业务代码中应该只导入OpenTelemetry-API，而不是OpenTelemetry-SDK，包括使用的类型注解
# ------ metrics ------
from opentelemetry.metrics import set_meter_provider, get_meter, get_meter_provider
# 用于类型提示
from opentelemetry.metrics import (
    # MeterProvider,
    Meter, Instrument, Observation, CallbackOptions,
    Counter, ObservableCounter, UpDownCounter, ObservableUpDownCounter,
    _Gauge, ObservableGauge, Histogram
)
# from opentelemetry.metrics._internal.instrument import Gauge
# ------ traces ------
from opentelemetry.trace import (
    get_tracer, get_tracer_provider, set_tracer_provider, get_current_span, use_span, set_span_in_context,
    # TracerProvider,
    Tracer, TraceState, TraceFlags, Span, SpanContext, SpanKind, Status, StatusCode
)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
# ------ logs ------
# 实际上，和 Metric、Trace 使用不一样，OTel里的Log采用桥接方式使用，因此业务代码里永远不要直接使用 Logs-API 提供的内容。
from opentelemetry._logs import Logger, LogRecord, SeverityNumber, get_logger, get_logger_provider, set_logger_provider
# from opentelemetry._logs import LoggerProvider
# ------ context propagator ------
# 只有API里有，SDK里没有相关内容
from opentelemetry.context import Context, get_current, attach, detach, create_key, get_value, set_value
from opentelemetry.propagators import textmap, composite
from opentelemetry.propagate import set_global_textmap, get_global_textmap, inject, extract
from opentelemetry.baggage import set_value, get_baggage, remove_baggage, clear
from opentelemetry.baggage.propagation import W3CBaggagePropagator
# %% --------------- 导入OpenTelemetry-SDK ---------------
# 业务代码中 OpenTelemetry-SDK 只在初始化配置 Provider 时使用
# ------ resource ------
# resource 只有SDK里有定义
from opentelemetry.sdk.resources import (
    Resource,
    OS_TYPE, OS_VERSION, OS_DESCRIPTION,
    HOST_NAME, HOST_ARCH, HOST_TYPE, DEPLOYMENT_ENVIRONMENT,
    SERVICE_NAME, SERVICE_NAMESPACE, SERVICE_VERSION, SERVICE_INSTANCE_ID,
    # TELEMETRY_SDK_LANGUAGE, TELEMETRY_SDK_NAME, TELEMETRY_SDK_VERSION,
)
# ------ metrics ------
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricReader, MetricExporter, MetricExportResult, MetricsData,
    InMemoryMetricReader, PeriodicExportingMetricReader, ConsoleMetricExporter
)
from opentelemetry.sdk.metrics import AlwaysOffExemplarFilter, AlwaysOnExemplarFilter, TraceBasedExemplarFilter
from opentelemetry.sdk.metrics.view import (
    View, Aggregation, DefaultAggregation, DropAggregation,
    SumAggregation, LastValueAggregation, ExplicitBucketHistogramAggregation,
)
# ------ traces ------
from opentelemetry.sdk.trace import (
    Tracer, Span,
    TracerProvider, SpanLimits,
    SpanProcessor, SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import (
    Sampler, SamplingResult,
    StaticSampler, TraceIdRatioBased, ParentBased, ParentBasedTraceIdRatio,
    # 一般使用下面4个预定义的采样器就行了
    DEFAULT_ON, DEFAULT_OFF, ALWAYS_ON, ALWAYS_OFF,
)
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor, BatchSpanProcessor,
    SpanExporter, SpanExportResult, ConsoleSpanExporter,
)
# ------ logs ------
# OTel-Logs 主要使用 SDK 里提供的功能即可，不要在业务代码中直接使用 OTel-Logs-API 里的内容
from opentelemetry.sdk._logs import (
    LoggingHandler, LoggerProvider, LogRecordProcessor, LogRecordLimits,
    ReadableLogRecord, ReadWriteLogRecord
)
from opentelemetry.sdk._logs.export import (
    # LogRecordProcessor 这个抽象类在上面 opentelemetry.sdk._logs 里已导入了
    SimpleLogRecordProcessor, BatchLogRecordProcessor,
    LogRecordExporter, ConsoleLogRecordExporter, InMemoryLogRecordExporter,
    LogRecordExportResult,
    # LogExporter, ConsoleLogExporter, InMemoryLogExporter, # 这几个都是被标记为废弃的，指向上面的RecordExporter
)
# 生产环境请替换为: from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# %% --------------- OpenTelemetry-SDK: Resource 配置 ---------------
@lru_cache(maxsize=1)
def resource_configuration() -> Resource:
    """
    OTel Resource 配置。
    Resource 只在SDK里有定义和实现。
    """
    print("*********** resource_configuration start ***********")
    # 一般使用 Resource.create() 静态方法初始化一个Resource对象，而不是直接调用__init__
    resource = Resource.create(
        # attributes是一个dict，可以填入自定义属性，也可以使用OTel预定义的属性SERVICE_NAME, SERVICE_NAMESPACE, SERVICE_VERSION
        attributes={
            # OS_TYPE: os.name,
            OS_TYPE: platform.system(),
            OS_VERSION: platform.release(),
            OS_DESCRIPTION: platform.platform(),
            HOST_ARCH: platform.machine(),
            HOST_TYPE: platform.node(),
            HOST_NAME: socket.gethostname(),
            DEPLOYMENT_ENVIRONMENT: "dev",
            SERVICE_NAME: "micro.some.service",
            SERVICE_NAMESPACE: "micro.some",
            SERVICE_VERSION: "1.0.0",
            SERVICE_INSTANCE_ID: "1234567890",
            # 自定义属性
            "resource_tag": "some-resource-tag"
        },
        # 可选参数[since 1.4.0]，配置一个 Schema URL，指明该 Resource 所遵循的OTel语义约定（Semantic Conventions）的版本地址
        # schema_url="https://opentelemetry.io/schemas/1.21.0"
        # 实际中，一般使用 opentelemetry.semconv.schemas 提供的 Schemas 枚举变量值
        schema_url = Schemas.V1_40_0.value
    )
    print(f"resource: {resource.to_json()}")
    print("*********** resource_configuration done ***********")
    return resource


# %% --------------- OpenTelemetry-SDK: Metrics 配置 ---------------
def metrics_sdk_configuration_usage(views: List[View] | None = None):
    """
    展示OTel metrics sdk 的初始化配置。
    主要配置步骤为：
    1. 定义Resource;
    2. 配置 Reader + Exporter，其中 Exporter 是由 Reader 管理的;
    3. 配置 MeterProvider;
    4. 通过API提供的工具函数来注册 MeterProvider.

    内置的两种 MetricReader 如下：
    | 特性            | `InMemoryMetricReader`                   | `PeriodicExportingMetricReader`  |
    |----------------|------------------------------------------|----------------------------------|
    | 主要目的         | 拉取式 (Pull)：供外部主动查询当前指标快照                 | 推送式 (Push)：自动、周期性地将指标推送到后端       |
    | 典型用途         | 单元测试、健康检查端点 (`/metrics`)、Prometheus 拉取模型 | 生产环境，向 OTLP Collector、云监控等后端持续上报 |
    | 是否启动后台线程   | ❌ 否                                             | ✅ 是                              |
    | 数据生命周期      | 调用 `collect()` 时才聚合，之后数据通常被重置            | 数据在内存中累积，由后台线程定期导出并（通常）重置        |
    | 与 Exporter 关系 | 不直接使用 Exporter                                 | 必须 配合一个 `MetricExporter` 使用      |

    内置的 MetricExporter 只有 ConsoleMetricExporter 这一种。
    """
    print("*********** metrics_sdk_configuration ***********")
    # 1. 定义 Resource (标识数据来源)
    resource = resource_configuration()

    # 2. 配置 Exporter + Reader
    # 开发阶段用 Console；生产替换为 OTLPMetricExporter(endpoint="http://collector:4317")
    console_exporter = ConsoleMetricExporter()
    # 生产环境需要使用 PeriodicExportingMetricReader 定期将数据导出到 Exporter
    reader = PeriodicExportingMetricReader(
        exporter=console_exporter,
        export_interval_millis=5000  # 开发时可设短一些，生产建议 15s-60s
    )
    # 开发也可以使用 InMemoryMetricReader 方便测试断言
    # 不过要注意，InMemoryMetricReader 是 Pull 模式的，不需要配置 Exporter。
    memory_reader = InMemoryMetricReader()

    # 3. 组装 MeterProvider。这个 MeterProvider 是从SDK导入的
    provider = MeterProvider(
        metric_readers=[reader, memory_reader],
        resource=resource,
        # 配置视图
        views=views if views else []
    )

    # 4. 注册全局 MeterProvider，此函数是从 API 导入的
    set_meter_provider(provider)
    # ✅ 此后所有 get_meter() 调用都会使用此 Provider


# %% --------------- OpenTelemetry-API: Metric 使用 ---------------
def metrics_api_meter_init(views: List[View] | None = None) -> Meter:
    """
    """
    print("*********** metrics_api_meter_init ***********")
    # 先引入 SDK ，完成配置并注册
    metrics_sdk_configuration_usage(views)

    # 调用 API 提供的工具函数获取 Meter，此函数获取 Meter 实例的唯一入口，用于后续的指标创建。
    meter = get_meter(
        # 必填: Instrumentation Scope 的标识符，含义是标识"谁在产生这些指标"。
        # 它与 version、schema_url 共同组成一个唯一的 Instrumentation Scope。
        # 同一个 MeterProvider 下，相同 Scope 的多次 get_meter() 调用会返回同一个 Meter 实例（缓存机制）。
        # 命名规范：推荐使用反向域名 + 模块路径，与 Python 包名保持一致。
        # 例如："mycompany.orders.service"
        name='otel.metrics.usage.service',
        # 标识产生指标的代码/库的版本。
        version='1.0.0',
        # 指标语义约定版本，指向一个 YAML/JSON Schema 文件的 URL，描述该 Scope 下指标的语义约定版本
        schema_url=Schemas.V1_40_0.value,
        # 可选, ≥1.27.0：Scope 级静态属性
        # 附加到该 Meter 产生的所有指标上的固定键值对。等价于给整个 Scope 打一组全局标签。
        attributes={
            'meter-k1': 'meter-v1',
            'meter-k2': 'meter-v2'
        }
    )
    # 这个 meter 对象是全局使用的
    return meter


def metrics_api_counter_usage() -> None:
    """
    计数器Counter。
    语义：单调递增的累积值。只能加正数，不能减。用于统计"发生了多少次/多少个"。
    Counter 只有一个 add() 方法，参数为：
      - amount: 本次 measurement 的递增值
      - attributes: 附加在本次 measurement 上的标签
      - context:
    Counter 是线程安全的，内部有锁保护，多线程并发 add 无问题。
    默认聚合方式：SDK 自动按 Attributes + 时间窗口做 Sum 聚合
    """
    print("*********** metrics_api_counter_usage ***********")
    meter = metrics_api_meter_init()
    # 同步版本
    counter: Counter = meter.create_counter(
        name="http.requests.total",
        unit="1",  # 无量纲用 "1"，字节用 "By"，毫秒用 "ms"
        description="Total HTTP requests received"
    )
    # ✅ 使用：在请求处理中直接调用
    counter.add(1, {"method": "GET", "status_code": 200})
    counter.add(5, {"batch_type": "import"})  # 批量计数
    # ❌ 禁止：add 负数会被 SDK 静默丢弃并记录警告
    # counter.add(-1, {"method": "GET"})


def metrics_api_counter_usage_async() -> None:
    """
    异步计数器Counter。
    核心区别：不是主动 add（因为没有add方法），而是注册一个 callback，SDK 在每个导出周期拉取当前累计值。
    使用要点：
      - Callback 必须是轻量、快速的（< 1ms），因为它在 Reader 的导出线程中执行，阻塞会导致所有指标延迟
      - Callback 返回的是当前累计总值，不是增量。SDK 会自动计算两次采集之间的 delta
      - 支持传入多个 callback，SDK 会合并它们的结果
    """
    print("*********** metrics_api_counter_usage_async ***********")
    meter = metrics_api_meter_init()

    def _get_total_requests(callback: CallbackOptions) -> Iterable[Observation]:
        """回调函数，由 Reader 周期性调用"""
        # 从外部系统读取当前累计值
        # total = redis_client.get("global:request_count")
        total = 10
        yield Observation(int(total), {"source": "redis"})

    obs_counter: ObservableCounter = meter.create_observable_counter(
        name="http.requests.total.external",
        callbacks=[_get_total_requests],  # 👈 传入回调列表
        unit="1",
        description="Request count from external system"
    )


def metrics_api_gauge_usage():
    """
    同步仪表盘Gauge.
    语义：瞬时值，可上可下，反映"当前状态"。
    注意：早期 OTel 认为 Gauge 本质上都是"观测当前状态"，所以只提供异步版本。
    >= 1.25 版本后才新增了同步版本。

    Gauge只有一个 set() 方法，参数如下：
      - amount
      - attributes
      - context
    注意：set()方法是覆盖语义，不是累加。最后一次 set 的值就是该时间窗口内的 LastValue。
    """
    print("*********** metrics_api_gauge_usage ***********")
    meter = metrics_api_meter_init()

    gauge: _Gauge = meter.create_gauge(
        name="cache.hit_ratio",
        unit="1",
        description="Current cache hit ratio"
    )
    # ✅ 在业务逻辑中直接设置当前值
    gauge.set(0.85, {"cache_name": "user_profile"})
    gauge.set(0.72, {"cache_name": "session"})


def metrics_api_gauge_usage_async():
    """
    异步仪表盘Gauge.
    适用场景：CPU/内存/磁盘使用率、JVM/GC 指标、数据库连接池状态。
    """
    print("*********** metrics_api_gauge_usage_async ***********")
    meter = metrics_api_meter_init()

    def _get_memory_usage(callback: CallbackOptions) -> Iterable[Observation]:
        mem = psutil.virtual_memory()
        yield Observation(mem.percent, {"type": "virtual"})
        yield Observation(psutil.swap_memory().percent, {"type": "swap"})

    obs_gauge: ObservableGauge = meter.create_observable_gauge(
        name="system.memory.usage_percent",
        callbacks=[_get_memory_usage],
        unit="%",
        description="System memory utilization"
    )


def metrics_api_histogram_usage():
    """
    直方图Histogram。
    语义：记录值的分布。自动计算 min/max/sum/count 以及各桶边界内的计数。是 SLO/延迟分析的核心。
    注意：Histogram 没有异步版本，这是它的功能语义决定的。
    Histogram只有一个 record() 方法，参数如下：
      - amount
      - attributes
      - context
    默认桶边界可能不适合使用，因此生产环境需要通过 View 来自定义桶边界。
    """
    print("*********** metrics_api_histogram_usage ***********")
    meter = metrics_api_meter_init()

    histogram: Histogram = meter.create_histogram(
        name="http.response.duration",
        unit="ms",
        description="HTTP response latency distribution"
    )

    # ✅ 每次请求记录一个样本
    histogram.record(42.5, {"method": "GET", "endpoint": "/api/users"})
    histogram.record(1250.3, {"method": "POST", "endpoint": "/api/orders"})


def metrics_sdk_view_usage():
    """
    Metric-View使用。
    SDK 中 View 的作用是在原始 record 数据进入 Reader 导出之前，对其进行拦截和转换。

    注意：View 与 Exporter 是“多对多”的正交关系，每一个 MetricReader（及其绑定的 Exporter）都会独立地应用所有的 Views。
    本质上，View 属于 MeterProvider 的全局聚合配置，而不是绑定到 Exporter 上。

    class View 的初始化配置参数如下：

      --- 以下参数是用于定义 匹配规则 的，符合这些规则的就是当前View会处理的 Instrument（支持通配符*）
      - instrument_type:
      - instrument_name:
      - meter_name:
      - meter_version:
      - meter_schema_url:
      - instrument_unit:

      --- 以下参数是用于定义 自定义属性 的，用于对上述符合规则的 Instrument 进行处理
      - name: 重命名
      - description:
      - attribute_keys: 只有在这里声明的 key 才会被保留（白名单机制），防基数爆炸。
      - aggregation: 这里用于指定聚合规则配置 ------------- KEY
      - exemplar_reservoir_factory:
    """
    print("*********** metrics_sdk_view_usage ***********")
    # ✅ 只保留 method 和 status，丢弃所有高基数字段
    safe_http_view = View(
        # 匹配的 instrument name
        instrument_name="http.response.duration",
        # 显式声明只保留这些 attribute key，未列出的 key 会被静默丢弃
        attribute_keys={"method", "status_code", "endpoint_pattern"}
    )

    # 重命名与描述修改
    legacy_rename_view = View(
        # 匹配规则
        instrument_name="old.metric.name",
        instrument_unit="ms",  # 覆盖单位
        # ----- 修改属性 -----
        name="new.standard.name",  # 重命名
        description="Updated semantic convention",  # 覆盖描述
    )

    # 配置好的 View 是在 SDK 的 MeterProvider 中注册的，从而影响所有后续创建的 Meter
    # 一个 Provider 可以挂载多个 View，按顺序匹配，第一个匹配的生效（类似路由表）。
    meter = metrics_api_meter_init(views=[safe_http_view, legacy_rename_view])


def metrics_sdk_view_aggregate_usage():
    """
    Metric-View 配置 Aggregation。
    Aggregation 决定了同一个 Instrument + 同一组 Attributes 的数据点，在一个导出周期内如何被压缩。
    它只能作为 View 的参数传入。

    metrics SDK 内置的 Aggregation 策略如下表：

    | Aggregation                             | 适用 Instrument          | 行为                           | 典型场景          |
    |:----------------------------------------|:-----------------------|:-----------------------------|:--------------|
    | `DefaultAggregation`                    | 全部                     | 根据 Instrument 类型自动选择最合适的聚合方式 | 90%的场景直接用默认即可 |
    | `SumAggregation`                        | Counter, UpDownCounter | 累加所有值                        | 请求总数、字节数      |
    | `LastValueAggregation`                  | Gauge                  | 只保留最后一次 set 的值               | CPU使用率、连接池大小  |
    | `ExplicitBucketHistogramAggregation`    | Histogram              | 按指定桶边界分桶计数                   | 延迟分布（必配）      |
    | `ExponentialBucketHistogramAggregation` | Histogram              | 指数级动态桶边界                     | 高精度延迟分析，节省存储  |
    | `DropAggregation`                       | 全部                     | 直接丢弃该 Instrument 的所有数据       | 屏蔽不需要的内置指标    |
    """
    print("*********** metrics_sdk_view_aggregate_usage ***********")

    # View + Aggregate 典型场景：自定义 Histogram 的桶边界
    # 针对内部 gRPC 服务的低延迟优化桶
    grpc_latency_view = View(
        instrument_name="rpc.server.duration",
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=[0.1, 0.5, 1, 2, 5, 10, 25, 50, 100],  # 毫秒
            record_min_max=True  # 是否额外记录 min/max 值
        )
    )

    # 用 DropAggregation 降噪
    # 很多 OTel 自动插桩库（如 SQLAlchemy、Redis）会产生大量你不需要的细粒度指标。
    # 与其让它们消耗内存和存储，不如直接 Drop
    drop_redis_detail_view = View(
        instrument_name="db.redis.*",
        aggregation=DropAggregation()  # 完全屏蔽
    )

    meter = metrics_api_meter_init([grpc_latency_view, drop_redis_detail_view])

    histogram = meter.create_histogram(
        "rpc.server.duration",
        unit="ms",
        description="RPC server latency distribution"
    )
    histogram.record(
        amount=1000,
        attributes={"method": "GET", "service": "some-service"},
    )


# %% --------------- OpenTelemetry-SDK: Traces 配置 ---------------
def traces_sdk_configuration_usage():
    """
    展示 OTel-Trace-SDK 引入后的配置流程.
    整体配置流程为：
    1. 配置 Resource
    2. 配置采样策略 Sampler
    3. 配置 SpanLimits
    4. 初始化 TracerProvider，传入 Sampler 和 SpanLimits
    5. 初始化 SpanProcessor，并传入 Exporter
    6. 向 TracerProvider 挂载 SpanProcessor
    7. 调用 Tracer-API 工具方法，注册配置好的 TracerProvider

    OTel-Traces-SDK 里内置了如下两种 SpanProcessor:
    | 特性        | `SimpleSpanProcessor`    | `BatchSpanProcessor` |
    |------------|--------------------------|----------------------|
    | 处理模式     | 同步（Synchronous）       | 异步（Asynchronous）     |
    | 导出时机     | 每个 Span 结束时立即导出    | 积累一批 Span 后由后台线程批量导出 |
    | 是否阻塞应用线程 | ✅ 是（直到导出完成）     | ❌ 否（仅写入内存队列）         |
    | 性能影响     | 高（尤其在网络 I/O 场景下）   | 低（对主业务逻辑几乎无影响）       |
    | 资源开销     | 低（无额外线程）            | 中（需后台线程 + 内部队列）      |
    | 数据可靠性    | 高（每条 Span 都尝试导出）   | 中（队列满或进程崩溃可能丢数据）     |
    | 典型用途     | 开发调试、单元测试           | 生产环境（强烈推荐）           |

    OTel-Traces-SDK 里内置的 SpanExporter 只提供了 ConsoleSpanExporter 一种实现。
    """
    print("*********** traces_sdk_configuration ***********")
    # 1. 定义 Resource
    resource = resource_configuration()

    # 2. 配置采样策略
    sampler = ParentBasedTraceIdRatio(rate=0.5)  # 50% 采样率，且尊重上游决策

    # 3. 配置 SpanLimits
    span_limits = SpanLimits(
        max_attributes=128,
        max_attribute_length=256,
        max_events=128,
        max_links=128,
    )

    # 4. 创建 TracerProvider
    provider = TracerProvider(
        resource=resource,
        sampler=sampler,
        span_limits=span_limits
    )

    # 5. 实例化 SpanProcessor，配置 Exporter
    # 生产环境：BatchSpanProcessor + OTLP
    # otlp_exporter = OTLPSpanExporter(endpoint="otel-collector:4317")
    # batch_processor = BatchSpanProcessor(otlp_exporter)
    # 开发调试：可额外挂载 Console 输出
    simple_processor = SimpleSpanProcessor(ConsoleSpanExporter())

    # 6. 注册 SpanProcessor
    # provider.add_span_processor(batch_processor)
    # 开发调试：可额外挂载 Console 输出
    provider.add_span_processor(simple_processor)

    # 配置shutdown，优雅停机
    atexit.register(provider.shutdown)

    # 7. 使用 Tracer-API 提供的工具函数注册配置好的TracerProvider
    set_tracer_provider(provider)


# %% --------------- OpenTelemetry-API: Traces 使用 ---------------
def traces_api_usage():
    """
    OTel-Traces-API使用。
    主要关注两个类的使用：

    1. Tracer，由 get_tracer() 函数返回的 全局单例对象。
    主要方法如下：
    - start_as_current_span() —— 推荐方式（支持上下文管理器），主要参数如下：
      - name
      - context
      - kind
      - attributes
      - links
      - start_time
      适用大部分（同步）场景，会自动处理异常，自动调用 Span.end()，支持嵌套调用
    - start_span —— 手动管理方式，适用异步场景。

    2. Span，只能由 Tracer 创建。
    主要方法如下：
    - set_attribute(key, value) —— 添加元数据。
      适用场景：
      - 记录业务关键标识（用户ID、订单号）
      - 标记操作特征（重试次数、缓存命中/未命中）
    - add_event(name, attributes=None, timestamp=None) —— 记录离散事件
      适用场景：
      - 记录关键决策点（缓存未命中、降级触发）
      - 标记异步操作的阶段（“消息入队”、“任务开始执行”）
      - 替代结构化日志（当事件与 Span 强相关时）
    - record_exception(exception, attributes=None) —— 标准化异常
    - set_status(status_code, description="") —— 手动标记Span结果

    总结：
    | 对象      | 方法                     | 何时用                    | 何时不用                        |
    | -------- | ----------------------- | ------------------------ | ------------------------------ |
    | `Tracer` | `start_as_current_span` | 同步函数、Web 请求处理器     | 异步回调、手动 Context 管理        |
    | `Tracer` | `start_span`            | 异步任务、跨线程传递         | 普通业务逻辑（易出错）              |
    | `Span`   | `set_attribute`         | 业务标识、操作特征           | 敏感数据、高频变化值               |
    | `Span`   | `add_event`             | 关键决策点、阶段标记         | 替代日志全文（用 Logs）            |
    | `Span`   | `record_exception`      | 所有捕获的异常              | 未处理的异常（会被全局处理器捕获）    |
    | `Span`   | `set_status`            | 显式标记失败原因            | 成功场景（可省略）                 |
    | `Span`   | `is_recording`          | 高开销调试信息              | 简单属性设置                     |
    """
    print("*********** traces_api_usage ***********")
    # 引入Trace-SDK，并进行配置、注册
    traces_sdk_configuration_usage()

    # 1. 获取Tracer，推荐以模块名命名，便于后端区分来源
    tracer: Tracer = get_tracer(
        instrumenting_module_name="otel.traces.usage.service",
        instrumenting_library_version="1.0.0",
        schema_url=Schemas.V1_40_0.value,
        attributes={
            "trace-k1": "trace-v1",
            "trace-k2": "trace-v2",
        },
    )

    # 2. 创建 Span
    # 2.1 方式一：上下文管理器（推荐，自动处理异常记录和 Span 结束）
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("span.manager", "auto")
        span.set_attribute("order.id", "ORD-2026-001")
        span.set_attribute("order.items_count", 3)

        # 嵌套子 Span（自动建立 parent-child 关系）
        with tracer.start_as_current_span("validate_inventory") as child:
            child.set_attribute("sku", "ITEM-A")
            # ... 业务逻辑

    # 2.2 方式二：手动管理（适用于异步回调等无法用 with 的场景）
    span = tracer.start_span("async_callback")
    try:
        # ... 业务逻辑
        print("some business operation")
        span.set_attribute("span.manager", "manual")
        span.set_attribute("order.id", "ORD-2026-200")
        span.set_attribute("order.items_count", 10)
        span.set_status(StatusCode.OK)
    except Exception as e:
        span.record_exception(e)
        span.set_status(StatusCode.ERROR, str(e))
    finally:
        span.end()  # ⚠️ 必须手动调用，否则 Span 永远不会关闭


def traces_api_advanced_usage():
    """
    OTel-Traces-API 进阶用法演示：
    1. add_event() —— 记录离散事件（关键决策点、阶段标记）
    2. record_exception() —— 标准化异常记录
    3. SpanKind —— 语义化 Span 类型（CLIENT/SERVER/PRODUCER/CONSUMER/INTERNAL）
    4. links —— 跨 Trace 关联（如批处理任务关联多个上游请求）
    5. set_status —— 显式标记 Span 结果
    """
    print("*********** traces_api_advanced_usage ***********")
    traces_sdk_configuration_usage()

    tracer: Tracer = get_tracer(
        instrumenting_module_name="otel.traces.advanced.service",
        instrumenting_library_version="1.0.0",
        schema_url=Schemas.V1_40_0.value,
    )

    # ===== 1. add_event —— 记录关键决策点 =====
    print("\n--- 1. add_event: 记录缓存未命中事件 ---")
    with tracer.start_as_current_span("fetch_user_profile") as span:
        span.set_attribute("user.id", "U-10086")
        # 模拟缓存查询
        cache_hit = False
        if not cache_hit:
            span.add_event(
                "cache.miss",
                attributes={"cache.key": "user:U-10086", "cache.ttl": 300}
            )
        span.add_event("db.query.start", attributes={"table": "users"})
        # ... 模拟 DB 查询 ...
        span.add_event("db.query.done", attributes={"rows_returned": 1})

    # ===== 2. record_exception —— 标准化异常 =====
    print("\n--- 2. record_exception: 捕获并记录异常 ---")
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("payment.amount", 99.99)
        try:
            # 模拟支付失败
            raise ValueError("余额不足")
        except Exception as e:
            span.record_exception(e, attributes={"payment.status": "failed"})
            span.set_status(StatusCode.ERROR, f"支付失败: {e}")
            print(f"  ↳ 异常已记录到 Span: {e}")

    # ===== 3. SpanKind —— 语义化 Span 类型 =====
    print("\n--- 3. SpanKind: 不同类型 Span 的语义 ---")
    # SERVER: 处理外部传入的请求
    with tracer.start_as_current_span("GET /api/orders", kind=SpanKind.SERVER) as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.url", "/api/orders")

        # CLIENT: 向外发起的调用
        with tracer.start_as_current_span("redis GET", kind=SpanKind.CLIENT) as redis_span:
            redis_span.set_attribute("db.system", "redis")
            redis_span.set_attribute("db.operation", "GET")

        # INTERNAL: 内部操作（默认值）
        with tracer.start_as_current_span("serialize_response", kind=SpanKind.INTERNAL):
            pass  # 序列化逻辑

    # ===== 4. links —— 跨 Trace 关联 =====
    print("\n--- 4. links: 批处理任务关联多个上游 Span ---")
    # 模拟：先创建两个独立的上游 Span，然后在批处理 Span 中通过 links 关联它们
    upstream_span_1 = tracer.start_span("upstream_request_A")
    upstream_span_1.set_attribute("request.id", "REQ-A")
    upstream_span_1.end()

    upstream_span_2 = tracer.start_span("upstream_request_B")
    upstream_span_2.set_attribute("request.id", "REQ-B")
    upstream_span_2.end()

    # 批处理 Span，通过 links 关联上游
    from opentelemetry.trace import Link
    with tracer.start_as_current_span(
        "batch_process",
        links=[
            Link(context=upstream_span_1.get_span_context(), attributes={"role": "source"}),
            Link(context=upstream_span_2.get_span_context(), attributes={"role": "source"}),
        ]
    ) as batch_span:
        batch_span.set_attribute("batch.size", 2)
        batch_span.add_event("batch.processing.start")

    # ===== 5. set_status —— 显式标记 Span 状态 =====
    print("\n--- 5. set_status: 显式标记成功/失败 ---")
    with tracer.start_as_current_span("critical_operation") as span:
        success = True
        if success:
            span.set_status(StatusCode.OK, "操作成功完成")
        else:
            span.set_status(StatusCode.ERROR, "操作失败: 超时")


# %% --------------- OpenTelemetry-SDK: Logs 使用 ---------------
def logs_sdk_usage():
    """"
    OTel-Logs-SDK使用。

    OTel Logs 模块的设计哲学与 Metrics/Traces 有本质区别。
    在 Python 生态中，OTel Logs 不鼓励你直接使用 opentelemetry-api 的日志接口写业务代码，而是通过桥接（Bridge） 机制复用标准库 logging。
    桥接模式的工作原理如下：
      1. **应用继续使用 SLF4J/log4j/zap 等原有日志 API**
      2. **将日志框架的 Appender/Handler 替换为 OTel-Logs-SDK 提供的 Bridge Appender**
      3. Bridge Appender 内部调用 `LoggerProvider.getLogger()` 获取 Logger
      4. 将日志框架的 LogEvent 转换为 OTel `LogRecord` 并调用 `emit()`
      5. Bridge Appender 负责从日志框架的 MDC/Context 中提取 Trace Context 并注入
    这个过程中，完全不涉及 OTel-Logs-API，直接使用OTel-Logs-SDK就行了。

    OTel-Logs-SDK提供的 LoggingHandler 就是起到这样一个桥接器的作用：
      - 它本身作为一个 Handler，可以接入 Python 标准库 logging 提供的 Logger 对象的 handlers。
      - 它持有 SDK 的 LoggerProvider 对象，将标准库 logging 的日志进行转换并接入到OTel生态。
    不过 LoggingHandler 并不是 OTel-Logs-SDK 里的规范，因为作为桥接器，它在不同语言中的日志框架/组件里实现形式并不一样。

    OTel-Logs-SDK提供的组件工作流程为：
    LoggingHandler -> LoggingProvider -> LogRecordProcessor实现类 -> LogExporter实现类.

    此外，虽然 OTel-Logs-API/SDK 规范中对于 LogRecord 的要求是不可变的，但 Processor 链又需要对数据进行转换。
    为此Python SDK中新增了 ReadableLogRecord 和 ReadWriteLogRecord 这两个数据类，实现读写分离视图模式。

    OTel-Logs-SDK 里提供了如下两种 LogRecordProcessor实现类：
    | 特性    | `SimpleLogRecordProcessor`    | `BatchLogRecordProcessor` |
    |--------|-------------------------------|---------------------------|
    | 处理模式 | 同步 (Synchronous)           | 异步 (Asynchronous)         |
    | 工作方式 | 每产生一条日志，立即调用 Exporter 导出   | 将日志暂存到队列，由后台线程批量导出        |
    | 性能影响 | 高：日志记录会阻塞应用线程，直到导出完成   | 低：日志记录只写入内存队列，几乎不阻塞应用     |
    | 可靠性  | 高：每条日志都会被尝试导出               | 中：队列满或应用崩溃可能导致日志丢失        |
    | 资源消耗 | 低（无额外线程）                      | 中（需要后台线程和内存队程）            |
    | 典型用途 | 开发、调试、测试                      | 生产环境                      |

    OTel-Logs-SDK 里提供了如下两种 LogExporter实现类：
    | 特性      | `ConsoleLogRecordExporter`                 | `InMemoryLogRecordExporter`                                       |
    |----------|--------------------------------------------|-------------------------------------------------------------------|
    | 主要目的    | 开发/调试：将日志记录以人类可读的格式直接打印到控制台（stdout/stderr） | 测试：将日志记录暂存于内存列表中，供程序后续读取和断言                                       |
    | 数据去向    | 标准输出（通常是终端）                        | 内存中的一个 Python 列表 (`self._logs`)                                   |
    | 是否阻塞    | 否（同步打印，但非常快）                       | 否（只是 append 到列表）                                                  |
    | 生产环境适用性 | ❌ 不适用（性能差，无结构化）                | ❌ 不适用（内存会无限增长，有泄漏风险）                                              |
    | 核心方法    | `export(log_data)` → 序列化并打印           | `export(log_data)` → 存入 `_logs` 列表 `get_finished_logs()` → 返回所有日志 |
    要点：
      - InMemoryLogRecordExporter 不会将日志输出到控制台，必须显式调用 get_finished_logs() 方法获取日志
      - 这两个导出器都不应该用于生产环境！在生产环境中，应该使用如 OTLPLogExporter 这样的导出器，

    """
    print("*********** logs_sdk_usage ***********")
    # 1. 定义 Resource (标识数据来源)
    resource = resource_configuration()

    # 2. LogRecordLimits: 资源保护阀 (防止异常数据占用内存/发往后端)
    log_limits = LogRecordLimits(
        max_attributes=64,          # 单条日志最多保留64个属性 (默认128)
        max_attribute_length=1024,  # 单个属性值最大1KB (防止超长堆栈/SQL撑爆缓冲)
    )

    # 3. 初始化 LogProvider
    logger_provider = LoggerProvider(
        resource=resource,
        # limits=log_limits,  # 👈 将 Limits 注入 Provider  ---- 此方式不对，目前还没找到 LogLimits 的配置接入方式
    )

    # 4. Processor + Exporter: 处理管道与传输适配器
    # exporter = OTLPLogExporter(endpoint="otel-collector:4317")  # 生产环境推荐使用 OTLP gRPC Exporter
    exporter = ConsoleLogRecordExporter()     # 本地演示用 Console
    # exporter = InMemoryLogRecordExporter()  # 本地演示也可以使用 InMemory

    # 生产环境必须使用 BatchLogRecordProcessor
    batch_processor = BatchLogRecordProcessor(
        exporter=exporter,
        max_queue_size=2048,  # 内存队列上限，超限后新日志被丢弃
        schedule_delay_millis=5000,  # 每5秒强制刷新一次
        max_export_batch_size=512,  # 每批最多导出512条
        export_timeout_millis=30000,  # 单次网络请求超时30s
    )
    # 开发环境可以使用 SimpleLogRecordProcessor
    simple_processor = SimpleLogRecordProcessor(exporter)

    # logger_provider.add_log_record_processor(batch_processor)
    logger_provider.add_log_record_processor(simple_processor)

    # 4. 使用 LoggingHandler 作为桥接器，持有 SDK 的 LoggerProvider  -------------- KEY
    handler = LoggingHandler(
        level=logging.NOTSET,  # 👈 始终透传，由 stdlib logger 控制过滤
        logger_provider=logger_provider,
    )

    # 5. 接入标准库 --------------- KEY
    logger  = logging.getLogger(__name__)
    logger.addHandler(handler)

    # 6. 注册优雅退出 Hook (防丢日志)
    atexit.register(logger_provider.shutdown)

    # ========== 使用 ==========
    logger.info("<Info> Hello, OpenTelemetry info log record.")
    logger.warning("<Warning> Hello, OpenTelemetry warning log record.")
    logger.error("<Error> Hello, OpenTelemetry error log record.")


def logs_sdk_advanced_usage():
    """
    OTel-Logs 进阶用法演示：
    Logs ↔ Traces 关联 —— OTel 最具价值的特性之一。
    当在活跃 Span 的上下文中写日志时，日志会自动带上 trace_id 和 span_id，
    从而在 Jaeger/Grafana 等后端中将日志与 Trace 关联起来。
    """
    print("*********** logs_sdk_advanced_usage ***********")

    # 1. 初始化 Trace Provider
    traces_sdk_configuration_usage()

    # 2. 初始化 Log Provider (与 logs_sdk_usage 相同流程)
    resource = resource_configuration()
    logger_provider = LoggerProvider(resource=resource)
    exporter = ConsoleLogRecordExporter()
    simple_processor = SimpleLogRecordProcessor(exporter)
    logger_provider.add_log_record_processor(simple_processor)

    handler = LoggingHandler(
        level=logging.NOTSET,
        logger_provider=logger_provider,
    )

    # 注意：使用独立的 logger 名称避免与 logs_sdk_usage 中的 handler 重复
    logger = logging.getLogger("otel.logs.advanced")
    logger.addHandler(handler)
    atexit.register(logger_provider.shutdown)

    # 3. 获取 Tracer
    tracer: Tracer = get_tracer(
        instrumenting_module_name="otel.logs.advanced.service",
        instrumenting_library_version="1.0.0",
        schema_url=Schemas.V1_40_0.value,
    )

    # ===== 核心演示：在 Span 上下文中写日志 =====
    print("\n--- 在 Span 上下文中写日志，自动关联 trace_id ---")
    with tracer.start_as_current_span("create_order") as span:
        span.set_attribute("order.id", "ORD-2026-999")
        current_span = get_current_span()
        span_ctx = current_span.get_span_context()
        print(f"  当前 Span: trace_id={span_ctx.trace_id:#034x}, span_id={span_ctx.span_id:#018x}")

        # 在 Span 上下文中写日志 —— OTel 自动注入 trace_id 和 span_id
        logger.info("订单创建开始")
        logger.info("库存校验通过", extra={"sku": "ITEM-X", "quantity": 5})

        # 嵌套子 Span 中写日志
        with tracer.start_as_current_span("reserve_inventory") as child:
            child_ctx = child.get_span_context()
            print(f"  子 Span:   trace_id={child_ctx.trace_id:#034x}, span_id={child_ctx.span_id:#018x}")
            logger.warning("库存紧张，剩余不足", extra={"sku": "ITEM-X", "remaining": 3})

        logger.info("订单创建完成")

    # ===== 对比：Span 外部写日志（无 trace_id 关联）=====
    print("\n--- Span 外部写日志（无 trace_id 关联）---")
    logger.info("这是一条没有 Trace 上下文的日志")

    print("\n  ↳ 观察 ConsoleLogRecordExporter 输出：")
    print("     有 Span 上下文时 → 日志包含 trace_id + span_id")
    print("     无 Span 上下文时 → 日志不包含 trace_id / span_id")


# %% --------------- 异常场景演示 ---------------
def otel_exception_usage():
    """
    OTel 常见异常/边界场景演示。
    帮助初学者理解哪些操作会导致问题，以及如何避免。
    """
    print("*********** otel_exception_usage ***********")

    # ===== 场景1: Counter.add() 传入负数 =====
    print("\n--- 场景1: Counter.add() 传入负数会被静默丢弃 ---")
    metrics_sdk_configuration_usage()
    meter = get_meter(
        name='otel.exception.service',
        version='1.0.0',
        schema_url=Schemas.V1_40_0.value,
    )
    counter: Counter = meter.create_counter(
        name="exception.test.counter",
        unit="1",
        description="Test counter for exception demo"
    )
    # ✅ 正常操作
    counter.add(10, {"status": "ok"})
    print("  ↳ counter.add(10) → 正常")
    # ❌ 负数会被静默丢弃，SDK 内部记录警告
    counter.add(-5, {"status": "bad"})
    print("  ↳ counter.add(-5) → SDK 静默丢弃，不会抛异常，但控制台可能有 WARNING 日志")

    # ===== 场景2: Span 未调用 end() 的后果 =====
    print("\n--- 场景2: Span 忘记 end() 会导致数据丢失 ---")
    traces_sdk_configuration_usage()
    tracer: Tracer = get_tracer(
        instrumenting_module_name="otel.exception.trace.service",
        instrumenting_library_version="1.0.0",
        schema_url=Schemas.V1_40_0.value,
    )
    # ❌ 忘记调用 span.end() —— 该 Span 永远不会被导出
    leaked_span = tracer.start_span("leaked_span")
    leaked_span.set_attribute("will.this.be.exported", "no")
    print("  ↳ 创建了 'leaked_span' 但故意不调用 end()")
    print("  ↳ 观察 ConsoleSpanExporter 输出：该 Span 不会出现！")

    # ✅ 正确做法：用 with 语句自动管理
    with tracer.start_as_current_span("safe_span") as span:
        span.set_attribute("will.this.be.exported", "yes")
    print("  ↳ 'safe_span' 使用 with 语句，自动 end()，会被正常导出")

    # ===== 场景3: 采样率导致 Span 被丢弃 =====
    print("\n--- 场景3: 低采样率下部分 Span 被丢弃 ---")
    # traces_sdk_configuration_usage 使用 ParentBasedTraceIdRatio(rate=0.5)
    # 大约 50% 的 Span 不会被导出
    for i in range(10):
        with tracer.start_as_current_span(f"sampled_span_{i}") as span:
            span.set_attribute("index", i)
    print("  ↳ 创建了 10 个 Span，采样率 50%，预计只有约 5 个被导出")
    print("  ↳ 观察 ConsoleSpanExporter 输出：实际导出的 Span 数量")

    # ===== 场景4: 同一 Logger 重复添加 Handler =====
    print("\n--- 场景4: 重复添加 Handler 导致日志重复输出 ---")
    test_logger = logging.getLogger("otel.exception.logger")
    resource = resource_configuration()
    logger_provider = LoggerProvider(resource=resource)
    exporter = ConsoleLogRecordExporter()
    processor = SimpleLogRecordProcessor(exporter)
    logger_provider.add_log_record_processor(processor)

    handler_1 = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    test_logger.addHandler(handler_1)
    # ❌ 如果再次调用 addHandler，同一条日志会被导出两次
    # test_logger.addHandler(handler_1)  # 取消注释可观察重复输出
    test_logger.info("这条日志应该只出现一次")
    print("  ↳ 观察 ConsoleLogRecordExporter：每条日志应只出现一次")
    print("  ↳ 如果重复 addHandler，日志会重复输出")

    atexit.register(logger_provider.shutdown)


# %% --------------- OpenTelemetry-API: Context Propagation 使用 ---------------
def context_usage():
    """
    OTel-Context使用。
    OTel关于Context的规范中，只有 API 里有定义，SDK 里没有相关内容。
    
    OTel-API的Python实现里有关Context的模块如下：
    1. `opentelemetry.context` —— 进程内上下文的"存储仓库"
      - 作用：提供一个与执行环境（线程/协程）绑定的、全局可访问的键值存储，用于在单个进程内传递 Context。
      - 主要组件：
        - Context：一个不可变的字典，用于存放各种上下文对象
        - get_current()：获取当前活跃的 Context。
        - attach(context) / detach(token)：将 Context 设为当前活跃上下文，并返回一个 token 用于后续恢复。

    2. `opentelemetry.propagators` —— 传播器的"工具箱"
      - 作用：定义了 Propagator 的抽象接口，并提供了 标准协议的具体实现。
      - 主要组件：
        - TextMapPropagator (抽象基类)
        - TraceContextTextMapPropagator：W3C TraceContext 标准实现
        - CompositePropagator：组合多个 Propagator

    3. `opentelemetry.propagate` —— 传播器的"全局门面"
      - 作用：提供一个全局、单例的入口点，用于执行 inject 和 extract 操作。它是对 propagators 模块的封装和简化。
      - 主要工具函数：
        - inject(carrier, context=None)：将 Context 注入到 carrier（如 HTTP headers）
        - extract(carrier, context=None)：从 carrier 中提取 Context
      `propagate` 模块是开发者最常用的接口。
    """
    print("*********** context_usage ***********")

    # 先初始化 Trace Provider
    traces_sdk_configuration_usage()
    tracer: Tracer = get_tracer(
        instrumenting_module_name="otel.context.service",
        instrumenting_library_version="1.0.0",
        schema_url=Schemas.V1_40_0.value,
    )

    # ===== 1. 模拟上游服务注入 trace context 到 HTTP headers =====
    print("\n--- 1. inject: 上游服务将 Trace Context 注入到 carrier ---")
    carrier: Dict[str, str] = {}
    with tracer.start_as_current_span("upstream_service") as upstream_span:
        upstream_ctx = upstream_span.get_span_context()
        print(f"  上游 Span: trace_id={upstream_ctx.trace_id:#034x}, span_id={upstream_ctx.span_id:#018x}")
        # 将当前 Context 注入到 carrier（模拟 HTTP 请求头）
        TraceContextTextMapPropagator().inject(carrier)
        print(f"  注入后的 carrier: {carrier}")
        # 典型输出: {'traceparent': '00-<trace_id>-<span_id>-01'}

    # ===== 2. 模拟下游服务从 headers 提取 trace context =====
    print("\n--- 2. extract: 下游服务从 carrier 提取 Trace Context ---")
    extracted_context = TraceContextTextMapPropagator().extract(carrier)
    with tracer.start_as_current_span(
        "downstream_service",
        context=extracted_context,  # 👈 传入提取的 Context，建立父子关系
    ) as downstream_span:
        ds_ctx = downstream_span.get_span_context()
        print(f"  下游 Span: trace_id={ds_ctx.trace_id:#034x}, span_id={ds_ctx.span_id:#018x}")
        print(f"  ↳ trace_id 与上游一致，span_id 不同 → 父子关系建立成功！")

    # ===== 3. Baggage —— 跨服务传递业务数据 =====
    print("\n--- 3. Baggage: 跨服务传递自定义键值对 ---")
    from opentelemetry.baggage.propagation import W3CBaggagePropagator

    # 注入 Baggage
    with tracer.start_as_current_span("service_with_baggage") as span:
        from opentelemetry.baggage import set_baggage
        set_baggage("user.id", "U-10086")
        set_baggage("tenant.id", "T-42")
        carrier_with_baggage: Dict[str, str] = {}
        # 同时注入 TraceContext + Baggage
        W3CBaggagePropagator().inject(carrier_with_baggage, context=get_current())
        print(f"  Baggage carrier: {carrier_with_baggage}")

    # 提取 Baggage
    extracted_ctx = W3CBaggagePropagator().extract(carrier_with_baggage)
    from opentelemetry.baggage import get_all
    print(f"  提取的 Baggage: {get_all(extracted_ctx)}")

    # ===== 4. 手动 Context 管理 =====
    print("\n--- 4. 手动 Context 管理: attach/detach ---")
    custom_key = create_key("custom.data")
    ctx = set_value(custom_key, "hello-otel")
    token = attach(ctx)
    print(f"  当前 Context 中 custom.data = {get_value(custom_key)}")
    detach(token)
    print(f"  detach 后 custom.data = {get_value(custom_key)} (恢复为 None)")


ConsoleExporterDocstring = """
OTel-SDK的实现中，三大支柱的Exporter里，都提供了基于 Console 的输出：

- ConsoleMetricExporter
- ConsoleSpanExporter
- ConsoleLogRecordExporter

这里对此做个总结。

1. 三者特点如下：
| 特性    | 说明 |
| :---   | :--- |
| 目标    | 仅用于开发、调试和演示，绝非为生产环境设计。 |
| 输出方式 | 均通过 Python 内置的 `print()` 函数（或等效操作）将数据写入 标准输出（stdout）。 |
| 输出行为 | 追加显示（Append），而非刷新或覆盖控制台。每条新数据都会在控制台上新增一行或多行。 |
| 数据格式 | 输出的是 结构化的、人类可读的 JSON 或类 JSON 字符串，便于开发者直接查看内容。 |
| 无状态   | 它们自身不维护任何状态（如 Metrics 的聚合状态由 Reader/Controller 管理），只负责“打印”。 |

2. 控制台输出行为总结：
| Exporter | 触发模式 | 输出频率 | 控制台行为 | 典型搭配 Processor |
| :--- | :--- | :--- | :--- | :--- |
| `ConsoleSpanExporter` | 推模式 (Push) | 每个 Span 结束时 | 追加 一条 JSON | `SimpleSpanProcessor` |
| `ConsoleLogRecordExporter` | 推模式 (Push) | 每条日志产生时 | 追加 一条 JSON | `SimpleLogRecordProcessor` |
| `ConsoleMetricExporter` | 拉模式 (Pull) | 周期性 (e.g., 每60秒) | 追加 一个 JSON 数组 | `PeriodicExportingMetricReader` |
"""


# %% --------------- Main ---------------
def main():
    """
    按模块依次展示 OpenTelemetry Metrics / Traces / Logs / Context / 异常场景 的效果。
    每个 Metrics 函数使用 PeriodicExportingMetricReader（5s 导出间隔），
    因此调用后需 sleep 等待导出完成。
    """
    SEP = "=" * 60
    sleep_seconds = 6  # PeriodicExportingMetricReader 默认 5s，多留 1s 余量

    # ==================== Part 1: Metrics 基础 ====================
    def _metrics_show():
        print(f"\n{SEP}")
        print("  PART 1: Metrics — Counter (同步)")
        print(SEP)
        metrics_api_counter_usage()
        time.sleep(sleep_seconds)

        print(f"\n{SEP}")
        print("  PART 1: Metrics — Counter (异步/可观测)")
        print(SEP)
        metrics_api_counter_usage_async()
        time.sleep(sleep_seconds)

        print(f"\n{SEP}")
        print("  PART 1: Metrics — Gauge (同步)")
        print(SEP)
        metrics_api_gauge_usage()
        time.sleep(sleep_seconds)

        print(f"\n{SEP}")
        print("  PART 1: Metrics — Gauge (异步/可观测)")
        print(SEP)
        metrics_api_gauge_usage_async()
        time.sleep(sleep_seconds)

        print(f"\n{SEP}")
        print("  PART 1: Metrics — Histogram")
        print(SEP)
        metrics_api_histogram_usage()
        time.sleep(sleep_seconds)

        print(f"\n{SEP}")
        print("  PART 1: Metrics — View (属性过滤 & 重命名)")
        print(SEP)
        metrics_sdk_view_usage()
        time.sleep(sleep_seconds)

        print(f"\n{SEP}")
        print("  PART 1: Metrics — View Aggregation (自定义桶边界)")
        print(SEP)
        metrics_sdk_view_aggregate_usage()
        time.sleep(sleep_seconds)

    # ==================== Part 2: Traces 基础 ====================
    def _traces_show():
        print(f"\n{SEP}")
        print("  PART 2: Traces — Span 创建 & 嵌套")
        print(SEP)
        traces_api_usage()
        # SimpleSpanProcessor 是同步导出，无需 sleep

    # ==================== Part 3: Traces 进阶 ====================
    def _traces_advanced_show():
        print(f"\n{SEP}")
        print("  PART 3: Traces — 进阶 (add_event/record_exception/SpanKind/links/set_status)")
        print(SEP)
        traces_api_advanced_usage()
        # SimpleSpanProcessor 是同步导出，无需 sleep

    # ==================== Part 4: Logs 基础 ====================
    def _logs_show():
        print(f"\n{SEP}")
        print("  PART 4: Logs — 桥接模式 (stdlib logging → OTel)")
        print(SEP)
        logs_sdk_usage()
        # 当前使用 SimpleLogRecordProcessor（同步），无需 sleep

    # ==================== Part 5: Logs ↔ Traces 关联 ====================
    def _logs_advanced_show():
        print(f"\n{SEP}")
        print("  PART 5: Logs — 进阶 (Logs ↔ Traces 关联)")
        print(SEP)
        logs_sdk_advanced_usage()
        # SimpleLogRecordProcessor + SimpleSpanProcessor 都是同步，无需 sleep

    # ==================== Part 6: Context Propagation ====================
    def _context_show():
        print(f"\n{SEP}")
        print("  PART 6: Context Propagation (inject/extract/baggage/attach)")
        print(SEP)
        context_usage()
        # SimpleSpanProcessor 同步导出，无需 sleep

    # ==================== Part 7: 异常场景 ====================
    def _exception_show():
        print(f"\n{SEP}")
        print("  PART 7: 异常场景 (负数Counter/忘记end/采样丢弃/重复Handler)")
        print(SEP)
        otel_exception_usage()
        time.sleep(sleep_seconds)  # Metrics 部分需要等待导出

    _metrics_show()
    _traces_show()
    _traces_advanced_show()
    _logs_show()
    _logs_advanced_show()
    _context_show()
    _exception_show()

    print(f"\n{SEP}")
    print("  全部演示完成！")
    print(SEP)


if __name__ == "__main__":
    main()
