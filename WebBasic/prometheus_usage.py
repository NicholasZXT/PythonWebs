"""
展示 Prometheus Python SDK 的使用。
Prometheus Python SDK 主要分为两个部分：

（一）指标收集
这部分包括：
- 具体指标类：Counter, Gauge, Histogram, Summary
- 指标收集的默认实例：REGISTRY
REGISTRY 是一个 全局的 CollectorRegistry 对象，所有的指标类在实例化时都有一个 registry 参数，该参数默认值就是全局的 REGISTRY 对象，
在 Metric 类的实例方法里，会调用 CollectorRegistry.register(self) 方法，将当前指标对象注册到 REGISTRY 里，
通过这种方式将 Metric 和 Registry 后台联系起来。

（二）指标服务暴露
有如下几种方式：
（1）收集指标，手动编写服务暴露。
    通过 generate_latest 函数收集当前的所有指标，输出文本格式. 该函数也有一个 registry 参数，默认值也是全局的 REGISTRY 对象。
    手动写一个HTTP服务，返回上面的文本格式指标，设置 ContentType = CONTENT_TYPE_LATEST。
    这种方式最基础，最灵活，也比较麻烦。
（2）使用 make_wsgi_app, make_asgi_app 函数生成一个可直接集成到 WSGI/ASGI 应用中的“子应用”或“可调用对象”，专门用于响应 Prometheus 抓取请求。
    这两个函数也有 registry 参数，默认值也是全局的 REGISTRY 对象。
    这种方式最方便，最为推荐，最容易和 Flask/FastAPI 集成。
（3）使用 start_http_server / start_wsgi_server 启动一个线程来专门执行指标暴露的HTTP服务，适用于简单场景，性能不高。
（4）使用 push_to_gateway 将指标推送到 Pushgateway
"""
from prometheus_client import Counter, Gauge, Histogram, Summary, REGISTRY
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, make_wsgi_app, make_asgi_app, start_http_server, start_wsgi_server
from prometheus_client import CollectorRegistry, push_to_gateway, delete_from_gateway
import random

def metric_usage():
    """
    展示 Prometheus 指标类使用。
    所有的Prometheus指标类 Counter, Gauge, Histogram, Summary，初始化都支持一个 labelsnames 参数，用于指定标签列表，
    作用是为该指标值设置 label，用于多维分析。
    要注意的是，如果初始化没有设置 labels，后续调用指标方法时也不能设置；
    初始化时设置了 labels，后续调用指标方法前，也必须要设置 labels 的值，顺序和定义时保持一致
    :return:
    """
    # -------- Counter，计数器，只增不减，适合累计值场景 --------
    # 定义一个 Counter
    request_total = Counter(
        name='http_requests_total',  # 指标名
        documentation='Total number of HTTP requests',  # 帮助文档
        labelnames=['method', 'status']  # 标签列表（可选）
    )
    print(request_total.describe())
    # 使用：增加计数
    # 由于上面初始化时设置了 labelsnames，下面在调用 inc() 之前也必须要设置 labels 的值，顺序和定义时保持一致，否则会报错
    request_total.labels(method='GET', status='200').inc()    # +1
    request_total.labels(method='POST', status='500').inc(3)  # +3
    # 下面这个 collect() 方法似乎作用不大，不是给客户端直接使用的
    rs = request_total.collect()
    print(rs)

    # -------- Gauge，仪表盘（可增可减） --------
    temperature = Gauge('room_temperature_celsius', 'Current room temperature')
    # 设置绝对值
    temperature.set(23.5)
    # 模拟变化
    temperature.inc(0.5)  # +0.5 → 24.0
    temperature.dec(1.0)  # -1.0 → 23.0

    # 也可用回调函数动态获取值（高级用法）
    disk_usage = Gauge('disk_usage_percent', 'Disk usage percentage')

    def get_disk_usage():
        return random.uniform(30, 90)  # 模拟读取

    disk_usage.set_function(get_disk_usage)

    # -------- Histogram，直方图分布统计（自动分桶），推荐用于延迟/大小分布 --------
    # 定义 Histogram，可自定义桶（buckets）
    request_duration = Histogram(
        'request_duration_seconds',
        'Request duration in seconds',
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0]  # 默认包含 +Inf
    )
    # 记录一次观测值（单位：秒）
    request_duration.observe(0.73)  # 自动落入 le="1.0" 桶

    # 也可带标签
    db_query_duration = Histogram(
        'db_query_duration_seconds',
        'Database query duration',
        ['table']
    )
    db_query_duration.labels(table='users').observe(0.045)

    # -------- Summary，分位数摘要（客户端计算） --------
    # 谨慎使用，因为数据会在客户端完成聚合，上报后就失去明细记录了
    # 定义 Summary（自动计算分位数）
    request_latency = Summary(
        'request_latency_seconds',
        'Request latency in seconds',
        ['endpoint']
    )
    # 记录观测值
    request_latency.labels(endpoint='/api/users').observe(0.12)

    # -------- 全局注册表 REGISTRY --------
    # 所有指标默认注册到 全局注册表 REGISTRY 中
    # 查看已注册的指标名
    metric_name = [metric.name for metric in REGISTRY.collect()]
    for name in metric_name:
        print(name)


def metric_expose():
    """
    指标暴露
    :return:
    """
    # 使用 generate_latest 函数获取当前所有的指标值的文本格式
    metric_text_bytes = generate_latest()
    # 返回的是 bytes 类型
    print(type(metric_text_bytes))
    metric_text = metric_text_bytes.decode('utf-8')
    print(metric_text)
    # 获取指标值的文本表示后，配合 HTTP 服务器，将指标值返回给客户端，此时需要设置 ContentType = CONTENT_TYPE_LATEST
    ...

def metric_expose_server():
    """
    指标暴露服务
    :return:
    """
    # 使用下面两个方法构造 WSGI/ASGI 应用，然后集成到其他Web框架（比如Flask/FastAPI） 中，
    # 注意，挂载后只响应 GET 请求，返回指标值
    wsgi_endpoint = make_wsgi_app()
    asgi_endpoint = make_asgi_app()
    # 两者的类型都是 <class 'function'>
    print(type(wsgi_endpoint))
    print(type(asgi_endpoint))

    # Flask 挂载示例：
    from flask import Flask
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    app_flask = Flask(__name__)
    # 使用 DispatcherMiddleware 将 /metrics 路由到 metrics_app
    app_flask.wsgi_app = DispatcherMiddleware(app_flask.wsgi_app, {
        '/metrics': wsgi_endpoint
    })

    # FastAPI 挂载示例：
    from fastapi import FastAPI
    app_fastapi = FastAPI()
    # 挂载到 /metrics 路径
    app_fastapi.mount("/metrics", asgi_endpoint)

    # 或者启动一个线程来执行指标暴露的HTTP服务
    start_http_server(port=8088, addr='localhost')


def push_to_gateway_usage():
    """
    Pushgateway 推送指标
    :return:
    """
    # 创建一个 Prometheus 注册表，可选
    registry = CollectorRegistry()

    # 将当前进程的所有指标一次性推送到 Pushgateway。
    push_to_gateway(
        # gateway，Pushgateway 地址
        gateway='http://pushgateway.example.org:9091',
        # 必填。标识这一组推送的作业名称（对应 Prometheus 中的 {job="..."} 标签）
        job='my_batch_job',
        # registry 要推送的指标注册表，默认就是 REGISTRY，可省略
        registry=registry,  # 使用自定义注册表
        # （可选）HTTP 超时时间（秒），默认 30
        timeout=30
    )

    # 高级用法，额外分组：所有推送的指标会自动加上标签：instance="worker-01", region="us-east-1"
    push_to_gateway(
        gateway='http://localhost:9091',
        job='data_processor',
        # 使用 grouping_key 进行额外分组
        grouping_key={'instance': 'worker-01', 'region': 'us-east-1'},
        registry=REGISTRY
    )

    # 删除指标
    delete_from_gateway(
        gateway='http://localhost:9091',
        job='data_processor',
        # 指定特定分组指标
        grouping_key={'instance': 'worker-01'}
    )


def main():
    ...


if __name__ == '__main__':
    main()

