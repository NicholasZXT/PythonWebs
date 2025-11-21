"""
展示 Litestar 里依赖注入系统的使用。
Litestar 依赖系统的使用风格与 FastAPI 不太一样。

FastAPI中依赖的使用方式有如下特点：
- 基于 “函数参数 = Depends()” 这种形式，
  相当于为 函数参数 设置了一个 Depends(...) 默认值，但是这个默认值只有FastAPI框架可以理解并使用。
  这种方式占用了 参数默认值 语法，个人感觉容易引起混淆。
- 显式配置，比较直观，依赖关系显式可见，因为注入依赖的地方都要使用 Depends(...) 进行标识
- 分散式的，需要依赖注入的地方都要使用 Depends()，重复代码比较多
比如下面的例子里，就有两个地方用到了 Depends()，比较分散
```python
from fastapi import Depends, FastAPI
def get_db():
    return "db_conn"
# 参数 db 使用 Depends(...) 作为默认值，标识为依赖项
def get_user(db=Depends(get_db)):
    return {"user": "alice", "db": db}

@app.get("/me")
def read_user(user: dict = Depends(get_user)):  # 这里同样
    return user
```

Litestar中依赖使用有如下特点：
- 基于参数名 + 类型注解 + Provide()
- 隐式配置，参数名 和 依赖的注册key 相同，就能实现注入，不那么直观
- 集中式的配置，一般都是在 dependencies 字典里配置所有的依赖

此外，两者的依赖注入系统还有如下两个个人感觉比较重要的使用区别：
- 依赖返回值：
  - FastAPI 的 全局/Router 级别依赖无法获取返回值，只有视图函数的直接依赖可以获取返回值；
  - Litestar 所有依赖都通过 key 绑定，返回值可被任意 handler 使用，如果依赖没有返回值，key对应的值则为None。
- 依赖可选性：
  - FastAPI全局依赖会作用于每个视图函数，无法选择：一方面方便了确实需要全局配置的场景，另一方面也显得不那么灵活
  - Litestar全局依赖注册 ≠ 强制使用，是否注入取决于 视图函数 是否声明该参数名
FastAPI 的全局依赖更适合无状态的横切关注点（如认证、日志），但牺牲了取值能力和选择性。
在 Litestar 中，如果也需要一个“全局生效、无需在每个视图函数中显式声明”的依赖，并且只关心它的副作用（如认证、日志、设置上下文），
那么应该使用 Middleware，而不是依赖注入；
同样，如果一个依赖没有返回值（虽然这是允许的），在 Litestar 中更推荐的做法是考虑 Middleware 或者 Guard，尽量保证依赖有返回值——这是一个良好的实践。

Litestar 在这方面的设计更灵活、可组合，适合复杂业务依赖，它不像FastAPI中的依赖那样承担了混合场景的，而是按照职责进行了划分：
| 场景                                               | 推荐方案          |
| ------------------------------------------------- | ---------------- |
| 提供可被 handler 使用的值（如 DB 连接、服务实例）         | ✅ DI（依赖注入）  |
| 记录日志、设置请求上下文、认证检查等副作用                 | ✅ Middleware    |
| 权限校验（成功/失败）                                 | ✅ Guard         |
"""
from typing import TYPE_CHECKING
from litestar import Controller, Request, Response, get, post, put, delete, MediaType
from litestar.di import Provide
from litestar.params import Dependency
from config import AppSettings


def controller_dependency(request: Request) -> str:
    request.logger.info(f">>> controller_dependency called from request: {request.url}")
    return "controller_dependency_value"

def local_dependency(request: Request) -> str:
    request.logger.info(f">>> local_dependency called from request: {request.url}")
    return "local_dependency_value"


class DependencyController(Controller):
    """
    展示 Litestar 里依赖注入系统的使用。
    """
    path = "/dependency"
    tags = ['Dependency']

    # 定义Controller级别的依赖注入，以字典的形式配置：key就是后续使用时的参数名称，value使用Provide(...)标识为依赖
    # 多个依赖可以在这里统一配置 —— 集中申明
    dependencies = {
        "controller_dep": Provide(controller_dependency, sync_to_thread=False)
    }

    @get(
        path="/",
        sync_to_thread=False,
        # 定义视图函数级别的依赖注入，也可以有多个。不过一般在Controller级别配置比较好，方便统一管理。
        dependencies={
            "local_dep": Provide(local_dependency, sync_to_thread=False)
        },
        summary="依赖注入基本使用",
        description="展示 Litestar 里依赖注入系统的使用",
        media_type=MediaType.JSON
    )
    def show_dependency(
            self,
            # 参数名 和 Controller 级别的依赖注册key一致，所以实际参数由依赖注入控制 —— 隐式注入，不那么直观
            controller_dep: str,
            # 参数名 和 视图函数级别的依赖注册key匹配
            local_dep: str,
            # 来源于Litestar对象全局依赖注入的 key
            app_settings: AppSettings,
    ) -> dict:
        data = {
            "controller_dep": controller_dep,
            "local_dep": local_dep,
            "app_settings": app_settings.model_dump(),
        }
        return data
