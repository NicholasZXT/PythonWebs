[TOC]

# FastAPI重要更新节点
参考官方发布的[release note](https://fastapi.tiangolo.com/release-notes/#release-notes).

+ 从 [0.100.0](https://fastapi.tiangolo.com/release-notes/#01000)版本起，FastAPI使用的Pydantic正式从 `pydantic-v1`升级到`pydantic-v2`了.

------
# 常用插件
可以参考[Github: Awesome FastAPI](https://github.com/yshan2028/awesome-fastapi/blob/main/README.md)

## 数据库

- [SQLModel](https://sqlmodel.tiangolo.com/)
  - FastAPI作者写的数据库模块，专门配合FastAPI使用，不过尚未到正式版
  - 对于sqlalchemy的版本有要求比较严格，基本上要求 2.0 以上，安装的时候需要注意 
```shell
pip install sqlmodel
conda install -c conda-forge sqlmodel 
```

- [Fastapi-SQLA](https://github.com/dialoguemd/fastapi-sqla)
  - 已发布正式版（v.3.4.8），持续更新中，更新频率较高
  - 支持分页，异步，SQLModel
  - 对于sqlalchemy的版本要求比较宽松
```shell
pip install fastapi-sqla
# conda暂无
```

- [FastAPI-SQLAlchemy](https://github.com/mfreeborn/fastapi-sqlalchemy)]
  - 未到正式版，v.0.2.1 发布于2020年，后续没有再更新 
```shell
pip install fastapi-sqlalchemy
# conda暂无
```

---
## RESTful

- [FastAPI-Utils](https://fastapi-utils.davidmontague.xyz/)
  - 未发布正式版，v0.6.0发布于2024年，缓慢更新中
  - 提供的CBV用起来不错
```shell
pip install fastapi-restful  # For basic slim package :)
pip install fastapi-restful[session]  # To add sqlalchemy session maker
pip install fastapi-restful[all]  # For all the packages
conda install -c conda-forge fastapi-restful 
```

- [~~FastAPI-Router-Controller~~](https://github.com/KiraPC/fastapi-router-controller)
  - 未发布正式版，v0.5.0发布于2022年，后续未更新
  - 此插件源代码比较少，可以看看
  - 此插件不是很好用，不推荐
```shell
pip install fastapi-router-controller
# conda暂无
```

---
## 认证
> 总结：
> + JWT认证功能的话，FastAPI-Login最好用，其次是 AuthX

- [FastAPI-Login](https://fastapi-login.readthedocs.io/), [Github地址](https://github.com/MushroomMaula/fastapi_login)
  - 已发布正式版(v1.10.3)，持续更新中 
  - 和Flask-Login插件不一样，这个主要提供基于JWT的认证（也支持基于session+cookies的认证），用法和Flask-Login类似
  - 此插件提供了token生成和验证功能，**支持 scope 权限控制**
  - 但**没有提供双token刷新**认证功能，不过是作者有意不添加此功能的，参见Issue[refresh token function #45](https://github.com/MushroomMaula/fastapi_login/issues/45)
```shell
pip install fastapi-login
# conda暂无
```

- [AuthX](https://authx.yezz.me/)，gthub地址：[AuthX](https://github.com/yezz123/AuthX?tab=readme-ov-file)
  - 已发布正式版(v1.4.1)，持续更新中
  - 此插件比较高的要求就是Pydantic 的版本要求 >= 2.0.0
  - 支持JWT，**支持双token刷新**认证功能
  - 但是**不支持 scope 权限控制**
```shell
pip install authx
# conda暂无
```

- [FastAPI Users](https://fastapi-users.github.io/fastapi-users/latest/)
  - 已发布正式版(v14.0.1)，持续更新中 
  - 此插件对于sqlalchemy的版本要求 >= 2.0.0
  - 此插件属于比较重的插件，依赖比较多，类似于Flask-Security，管的有点多，因为包含了用户管理的功能
```shell
pip install 'fastapi-users[sqlalchemy]'
conda install -c conda-forge fastapi-users
```

- [FastAPI-Auth-JWT](https://deepmancer.github.io/fastapi-auth-jwt/)，[Github地址](https://github.com/deepmancer/fastapi-auth-jwt)
  - 未到正式版，当前只到v0.1.11，但是项目于2024年发布，目前一直在更新中
  - 以中间件的形式提供JWT认证，不太好
  - 不提供双token刷新，也不提供scope权限控制
```shell
pip install fastapi-auth-jwt
# conda暂无
```

- [~~FastAPI Security~~](https://jacobsvante.github.io/fastapi-security/), [Github地址](https://github.com/jacobsvante/fastapi-security)
  - 未到正式版，v.0.5.0发布于2022年，后续未更新 
```shell
pip install fastapi-security
pip install fastapi-security[oauth2]
# conda暂无
```

- [~~FastAPI-JWT-Auth~~](https://indominusbyte.github.io/fastapi-jwt-auth/)，[Github地址](https://github.com/IndominusByte/fastapi-jwt-auth?tab=readme-ov-file)
  - 未到正式版，v0.5.0版本发布于2020年，后续未更新 
```shell
pip install fastapi-jwt-auth
# conda暂无
```

- [FastAPI-permissions](https://github.com/holgi/fastapi-permissions)
  - Row-level 权限控制
  - 未到正式版，v0.2.7版本发布于2020年，后续未更新 
```shell
pip install fastapi_permissions
# conda暂无
```

- [~~FastAPI Auth~~](https://github.com/dmontagu/fastapi-auth)
```shell
# 暂未上架PyPI
```


----------
# 认证&鉴权

## 概览
FastAPI提供的安全认证相关的组件都在`fastapi.security`模块里，分成了3类认证方案：
1. 基于标准HTTP的身份验证
2. 基于OAuth2的授权机制
3. 基于APIKey的特定密钥，这个此处不介绍

> FastAPI 里的认证和鉴权机制，都是采用依赖注入的方式实现的。

## 基于标准HTTP身份验证
这部分相关的类都在`fastapi.security.http`模块里，主要是如下3个类：
+ `HTTPBasic`，返回值是 `HTTPBasicCredentials` 模型
+ `HTTPBearer`，返回值是 `HTTPAuthorizationCredentials` 模型
+ `HTTPDigest`，返回值是 `HTTPAuthorizationCredentials` 模型

FastAPI提供的上述类，其实功能都很简单，查看源码就能发现，它们的功能就是作为视图函数的依赖注入，从请求header里解析出对应的信息，
但是**后续的处理逻辑交由开发者**。

**这些类并不提供token生成、验证等功能，这些都需要开发者自己完成**。

## 基于OAuth2授权机制
这部分相关的类都在`fastapi.security.oauth2`模块里，主要是如下3个类：
+ `OAuth2`，这是基类，一般不会之间直接使用这个类，而是使用下面几个
+ `OAuth2PasswordBearer`
+ `OAuth2AuthorizationCodeBearer`

此外还有两个Form类，用于从表单中获取用户名和密码等信息
+ `OAuth2PasswordRequestForm`
+ `OAuth2PasswordRequestFormStrict`

和HTTP身份验证里一样，这些类都只是简单的从请求header里解析对应信息，token验证和token生成功能都需要开发者自己完成。

---------
# 原理研究

## 依赖注入的实现

FastAPI的依赖注入过程主要由下面几个地方完成：
+ `fastapi.dependencies.models.Dependant`类，这个类封装了依赖的参数、函数、函数的返回值等信息
+ `fastapi.dependencies.utils`，依赖解析的工具函数都在这里，特别是其中的`get_dependant`、`analyze_param`、`solve_dependencies`这三个函数
+ `fastapi.routing` 的 `APIRouter` 和 `APIRoute`类

依赖注入的过程是在视图函数注册时（例如使用`@app.get`）进行的，大致流程如下：
+ 所有的视图函数注册，都是走`APIRouter`的`add_api_route`方法，此方法负责封装视图函数的上下文，将待注册的视图函数作为 endpoint 封装到`APIRoute`中
+ `APIRoute`实例化时，会调用`get_dependant`方法
+ `get_dependant`里，会对endpoint（视图函数）的参数逐层进行解析，查看有无`Depends`封装的依赖，逐层封装成`Dependant`对象
+ endpoint里的视图函数本身也会作为`Dependant`对象，封装到`dependant.call`属性里

粗略看下来，FastAPI的依赖注入和解析过程比较直白，没有太高深的设计，并且和Starlette没有关系，只能用于FastAPI，不是作为一个通用的依赖注入框架设计的。
