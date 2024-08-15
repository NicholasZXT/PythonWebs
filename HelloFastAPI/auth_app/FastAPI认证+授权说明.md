
# 概览
FastAPI提供的安全认证相关的组件都在`fastapi.security`模块里，分成了3类认证方案：
1. 基于标准HTTP的身份验证
2. 基于OAuth2的授权机制
3. 基于APIKey的特定密钥，这个此处不介绍

# 基于标准HTTP身份验证
这部分相关的类都在`fastapi.security.http`模块里，主要是如下3个类：
+ `HTTPBasic`，返回值是 `HTTPBasicCredentials` 模型
+ `HTTPBearer`，返回值是 `HTTPAuthorizationCredentials` 模型
+ `HTTPDigest`，返回值是 `HTTPAuthorizationCredentials` 模型

FastAPI提供的上述类，其实功能都很简单，查看源码就能发现，它们的功能就是作为视图函数的依赖注入，从请求header里解析出对应的信息，
后续的处理逻辑交由开发者。

这些类并不提供token生成、验证等功能，这些都需要开发者自己完成。


# 基于OAuth2授权机制
这部分相关的类都在`fastapi.security.oauth2`模块里，主要是如下3个类：
+ `OAuth2`，这是基类，一般不会之间直接使用这个类，而是使用下面几个
+ `OAuth2PasswordBearer`
+ `OAuth2AuthorizationCodeBearer`

此外还有两个Form类，用于从表单中获取用户名和密码等信息
+ `OAuth2PasswordRequestForm`
+ `OAuth2PasswordRequestFormStrict`

和HTTP身份验证里一样，这些类都只是简单的从请求header里解析对应信息，token验证和token生成功能都需要开发者自己完成。
