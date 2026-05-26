"""
OpenTelemetry实践练习
"""
from typing import Iterable, List, Set, Dict
import os
import psutil
import logging
import atexit
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
# ------ logs ------
# 实际上，和 Metric、Trace 使用不一样，OTel里的Log采用桥接方式使用，因此业务代码里永远不要直接使用 Logs-API 提供的内容。
from opentelemetry._logs import Logger, LogRecord, SeverityNumber, get_logger, get_logger_provider, set_logger_provider
# from opentelemetry._logs import LoggerProvider
# %% --------------- 导入OpenTelemetry-SDK ---------------
# 业务代码中 OpenTelemetry-SDK 只在初始化配置 Provider 时使用
# ------ resource ------
# resource 只有SDK里有定义
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_NAMESPACE, SERVICE_VERSION, HOST_NAME
from opentelemetry.semconv.schemas import Schemas
# ------ metrics ------
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.metrics import AlwaysOffExemplarFilter, AlwaysOnExemplarFilter, TraceBasedExemplarFilter
from opentelemetry.sdk.metrics.view import (
    View, Aggregation, DefaultAggregation, DropAggregation,
    SumAggregation, LastValueAggregation, ExplicitBucketHistogramAggregation,
)
# ------ traces ------
from opentelemetry.sdk.trace import (
    Tracer, Span,
    TracerProvider, SpanLimits, SpanProcessor,
    SynchronousMultiSpanProcessor, ConcurrentMultiSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import (
    Sampler, SamplingResult,
    StaticSampler, TraceIdRatioBased, ParentBased, ParentBasedTraceIdRatio,
    # 一般使用下面4个预定义的采样器就行了
    DEFAULT_ON, DEFAULT_OFF, ALWAYS_ON, ALWAYS_OFF,
)
from opentelemetry.sdk.trace.export import (
    SpanExporter, SpanExportResult, ConsoleSpanExporter,
    SimpleSpanProcessor, BatchSpanProcessor,
)
# ------ logs ------
from opentelemetry.sdk._logs import (
    LoggingHandler, LoggerProvider, LogRecordProcessor, LogRecordLimits,
    ReadableLogRecord, ReadWriteLogRecord
)
from opentelemetry.sdk._logs.export import (
    SimpleLogRecordProcessor, BatchLogRecordProcessor,
    LogRecordExporter, ConsoleLogRecordExporter, InMemoryLogRecordExporter,
    # LogExporter, ConsoleLogExporter, InMemoryLogExporter, # 这几个都是被标记为废弃的，指向上面的RecordExporter
)
# 生产环境请替换为: from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter


def resource_configuration() -> Resource:
    """
    OTel Resource 配置。
    Resource 只在SDK里有定义和实现。
    """
    print("*********** resource_configuration ***********")
    # 一般使用 Resource.create() 静态方法初始化一个Resource对象，而不是直接调用__init__
    resource = Resource.create(
        # attributes是一个dict，可以填入自定义属性，也可以使用OTel预定义的属性SERVICE_NAME, SERVICE_NAMESPACE, SERVICE_VERSION
        attributes={
            SERVICE_NAME: "my-service",
            SERVICE_NAMESPACE: "my-namespace",
            SERVICE_VERSION: "1.0.0",
            HOST_NAME: "my-host",
            # 自定义属性
            "service_tag": "some-tag"
        },
        # 可选参数[since 1.4.0]，配置一个 Schema URL，指明该 Resource 所遵循的OTel语义约定（Semantic Conventions）的版本地址
        # schema_url="https://opentelemetry.io/schemas/1.21.0"
        # 实际中，一般使用 opentelemetry.semconv.schemas 提供的 Schemas 枚举变量值
        schema_url = Schemas.V1_40_0.value
    )
    print(resource)
    return resource



def metrics_sdk_configuration_usage(views: List[View] | None = None):
    """
    展示OTel metrics sdk 的初始化配置
    """
    print("*********** metrics_sdk_configuration_usage ***********")
    # 1. 定义 Resource (标识数据来源)
    resource = resource_configuration()

    # 2. 配置 Exporter + Reader
    # 开发阶段用 Console；生产替换为 OTLPMetricExporter(endpoint="http://collector:4317")
    console_exporter = ConsoleMetricExporter()
    reader = PeriodicExportingMetricReader(
        exporter=console_exporter,
        export_interval_millis=5000  # 开发时可设短一些，生产建议 15s-60s
    )

    # 3. 组装 MeterProvider。这个 MeterProvider 是从SDK导入的
    provider = MeterProvider(
        metric_readers=[reader],
        resource=resource,
        # 配置视图
        views=views if views else []
    )

    # 4. 注册全局 MeterProvider，此函数是从 API 导入的
    set_meter_provider(provider)
    # ✅ 此后所有 get_meter() 调用都会使用此 Provider


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
        name='OTel-Metrics-Usage',
        # 标识产生指标的代码/库的版本。
        version='0.1.0',
        # 指标语义约定版本，指向一个 YAML/JSON Schema 文件的 URL，描述该 Scope 下指标的语义约定版本
        schema_url=Schemas.V1_40_0.value,
        # 可选, ≥1.27.0：Scope 级静态属性
        # 附加到该 Meter 产生的所有指标上的固定键值对。等价于给整个 Scope 打一组全局标签。
        attributes={
            "service.name": "mycompany.orders.service",
            "service.version": "0.1.0",
            "service.instance.id": "1234567890",
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
    drop_redis_detail = View(
        instrument_name="db.redis.*",
        aggregation=DropAggregation()  # 完全屏蔽
    )

    meter = metrics_api_meter_init([grpc_latency_view])

    histogram = meter.create_histogram(
        "rpc.server.duration",
        unit="ms",
        description="RPC server latency distribution"
    )
    histogram.record(
        amount=1000,
        attributes={"method": "GET", "service": "some-service"},
    )


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
    """
    print("*********** traces_sdk_configuration_usage ***********")
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
        instrumenting_module_name="some.service",
        instrumenting_library_version="1.0.0",
        schema_url=Schemas.V1_40_0.value,
        attributes={"service.name": "some-service"},
    )

    # 2. 创建 Span
    # 2.1 方式一：上下文管理器（推荐，自动处理异常记录和 Span 结束）
    with tracer.start_as_current_span("process_order") as span:
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
        span.set_status(StatusCode.OK)
    except Exception as e:
        span.record_exception(e)
        span.set_status(StatusCode.ERROR, str(e))
    finally:
        span.end()  # ⚠️ 必须手动调用，否则 Span 永远不会关闭


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
    exporter = ConsoleLogRecordExporter()   # 本地演示用 Console
    # exporter = InMemoryLogRecordExporter()  # 本地演示也可以使用 InMemory

    batch_processor = BatchLogRecordProcessor(
        exporter=exporter,
        max_queue_size=2048,  # 内存队列上限，超限后新日志被丢弃
        schedule_delay_millis=5000,  # 每5秒强制刷新一次
        max_export_batch_size=512,  # 每批最多导出512条
        export_timeout_millis=30000,  # 单次网络请求超时30s
    )

    logger_provider.add_log_record_processor(batch_processor)

    # 4. 使用 LoggingHandler 作为桥接器，持有 SDK 的 LoggerProvider
    handler = LoggingHandler(
        level=logging.NOTSET,  # 👈 始终透传，由 stdlib logger 控制过滤
        logger_provider=logger_provider,
    )

    # 5. 接入标准库
    logger  = logging.getLogger(__name__)
    logger.addHandler(handler)

    # 6. 注册优雅退出 Hook (防丢日志)
    atexit.register(logger_provider.shutdown)

    # ========== 使用 ==========
    logger.info("Hello, OpenTelemetry info log record.")

