[TOC]

Litestar 也是一个高性能的 ASGI Web 框架，根据官方文档[Litestar -> About -> Organization](https://litestar.dev/about/organization.html)，
早期名称为 Starlite，因为早期版本是基于另一个著名的 ASGI 框架 Starlette 开发的，
后来随着发展相对独立起来，最终于 2022.10 发布的 v1.39.0 版本摆脱了 Starlette 的依赖，并从 2.0 版本改名为 Litestar。


# 认证&鉴权
官方文档 [Usage -> Security](https://docs.litestar.dev/2/usage/security/index.html).

## 认证

Litestar 里的认证功能也是基于 Middleware 方式实现的，底层主要基于如下两个部分。

（1）`litestar.middleware` 里提供了认证相关的中间件抽象：

- `AuthenticationResult`: 一个简单的 dataclass，用于封装认证结果，包含如下两个属性：
  - `user`: 认证成功的用户信息，类型为`Any`
  - `auth`: 认证信息，类型为`Any`

- `AbstractAuthenticationMiddleware`: 认证中间件抽象类，实现了`MiddlewareProtocol`协议（但不是通过继承的方式）    
  这个抽象中间件类是挺抽象的，实现的功能很少（和`AbstractMiddleware`的抽象层次几乎一样），只有两个功能：
  - 定义了一个抽象异步方法`authenticate_request()`要求用户实现：
    - 方法签名为：`authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult`
    - 此方法体是空的，需要用户从 `ASGIConnection` 中获取请求头，解析认证信息，完成认证过程，并返回一个`AuthenticationResult`对象
  - 认证通过后，将`AuthenticationResult`对象中的`user`字段和`auth`分别存放到ASGI App中的 `Scope`里，供后续使用


（2）`litestar.security.base.py` 文件里，定义了SecurityBackend的抽象基类 `AbstractSecurityConfig`。    
这个抽象基类是Litestar提供的所有认证后端的基类，用户自定义认证后端时，也需要继承这个抽象类。   
此抽象基类主要有如下功能：
- 定义了一些认证所需的属性，比如：
  - `middleware`，认证中间件
  - `guards`，鉴权对象列表
- 实现了一个`on_app_init`方法，此方法应当在 `Litestar`初始化时的`on_app_init`属性里配置，它的逻辑很直白，干了下面一些事：
  - 将认证后端的 middleware 插入到`Litestar`实例的`middlewares`属性里，并且放到第一位
  - 将认证后端的 guard 插入到`Litestar`实例的`guards`属性里
  - 将认证后端的 dependence 插入到`Litestar`实例的`dependence`属性里
  - 配置OpenAPI文档所需的信息
  - 还有其他一些配置
- 实现了一个 `create_response()` 方法，感觉作用不大。

总之 `AbstractSecurityConfig` 里最重要的就是一些属性和`on_app_init`方法。


在上面两个抽象组件的基础上，Litestar 提供了如下几种认证后端：

### JWT认证

`litestar.security.jwt` package实现了JWT认证后端的功能。

主要分为如下几部分：

（1）`token.py`文件里，定义了一个dataclass数据类 `Token`：
- 封装JWT认证所需的属性信息
- **提供了JWT token生成、验证的一些静态方法，基于`jwt`包实现**。

（2）`middleware.py`文件里，定义了两个中间件类：
- `JWTAuthenticationMiddleware`，继承自上面的`AbstractAuthenticationMiddleware`
- `JWTCookieAuthenticationMiddleware`，继承了`JWTAuthenticationMiddleware`

`JWTAuthenticationMiddleware`中间件类实现了`authenticate_request()`方法，该方法里会从HTTP请求头中获取JWT token信息，
调用`Token`类的一些静态方法进行解析验证，返回一个`AuthenticationResult`对象。

该中间件初始化时有两个参数需要关注：
- `retrieve_user_handler`， 它是一个`Callable[[Token, ASGIConnection[Any, Any, Any, Any]], Awaitable[Any]]`，
  用于从解析完的JWT Token中获取用户信息，返回给`AuthenticationResult`对象，具体逻辑需要用户实现。
- `revoked_token_handler`，它是一个`Callable[[Token, ASGIConnection[Any, Any, Any, Any]], Awaitable[Any]]`，
  用于撤销JWT token，具体逻辑需要用户实现。

**不过这些中间件一般不需要用户手动引入，在实例化下面的 `BaseJWTAuth` 等认证后端时配置参数即可。**

（3）`auth.py`文件里定义了如下类：
- `BaseJWTAuth`，继承自`AbstractSecurityConfig`抽象类
- `JWTAuth`，继承自`BaseJWTAuth`，**JWT认证后端 —— 常用**
- `JWTCookieAuth`，继承自`BaseJWTAuth`
- `OAuth2PasswordBearerAuth`，继承自`BaseJWTAuth`，OAuth2认证后端

> 可惜的是，Litestar 好像没有提供 HTTP Basic 认证的实现。

`BaseJWTAuth` 在`AbstractSecurityConfig`抽象类的基础上，提供了如下方法的实现：
- `login()`，登录视图函数里使用此方法生成用户对应的JWT token Response，重要的参数如下：
  - `identifier: str`，用户唯一标识符
  - `token_expiration: timedelta`，token过期时间
- `create_token()`, 生成JWT token，参数基本和 `login()` 方法一样，返回token的字符串表示。

## 鉴权

参考官方文档 [Usage -> Security -> Guards](https://docs.litestar.dev/2/usage/security/guards.html).

Litestar里的鉴权功能对应的组件被称为 *Guards*。

一个 Guard 是一个 `Callable` 对象，接受两个参数：
- `connection: ASGIConnection`，ASGI连接对象及其子类，比较常用的是 `Request` 对象和 `WebSocket` 对象。
  - 经过认证中间件处理后，`connection`对象里会包含认证信息，通常使用 `ASGIConnection.user` 属性
- `route_handler: BaseRouteHandler`，路由处理对象。

Guard根据这两个信息来判断当前请求是否被允许访问对应的路由视图函数：
- 允许访问，则不抛异常，不必提供返回值
- 拒绝访问，则抛出异常，通常是 `HTTPException` 或者 `NotAuthorizedException`

Guard 也支持多个层次，从 Litestar 对象 -> routers / controllers -> 单个 route handlers，每个层次都可以有自己的
Guard，并且效果是累加的，只要有一个拒绝访问，则最终结果就是拒绝访问。