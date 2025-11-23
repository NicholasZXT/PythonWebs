[TOC]

# 常用插件
```shell
flask                     2.2.5           py310haa95532_0    http://mirrors.aliyun.com/anaconda/pkgs/main
flask-admin               1.6.1              pyhd8ed1ab_0    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-classful            0.16.0                   pypi_0    pypi
flask-httpauth            4.8.0              pyhd8ed1ab_0    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-jwt-extended        4.6.0              pyhd8ed1ab_0    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-login               0.6.3           py310haa95532_0    defaults
flask-principal           0.4.0              pyhd8ed1ab_2    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-restful             0.3.10             pyhd8ed1ab_0    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-security-too        5.1.2              pyhd8ed1ab_0    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-sqlalchemy          3.0.3              pyhd8ed1ab_0    http://mirrors.aliyun.com/anaconda/cloud/conda-forge
flask-wtf                 1.2.1           py310haa95532_0    defaults
```



---------
# RESTful插件

RESTful风格 在 Flask 中的插件实现主要有如下几个：
1. [Flask-RESTful](https://flask-restful.readthedocs.io/en/latest/index.html): 最早的Flask-REST项目，使用最广泛
   + GitHub仓库 [flask-restful](https://github.com/flask-restful/flask-restful)
   + PyPI版本只到 0.3.10，没有到正式版，但是GitHub仓库上的Release版本只到 0.2.12
   + 维护比较缓慢，可以尝试使用
2. [Flask-RESTPlus](https://flask-restplus.readthedocs.io/en/latest/): 后来开发，但是现在已经**不维护了**
   + GitHub仓库 [flask-restplus](https://github.com/noirbizarre/flask-restplus)
   + PyPI版本只到 0.13.0，没有到正式版，GitHub的Release版本保持一致
   + **已经差不多停止维护了**，参见[Issue770](https://github.com/noirbizarre/flask-restplus/issues/770)
3. [Flask-RESTX](https://flask-restx.readthedocs.io/en/latest/): 从 Flask-RESTPlus 仓库 fork 而来
   + GitHub仓库 [flask-restx](https://github.com/python-restx/flask-restx)
   + PyPI版本到 1.3.0，GitHub的Release版本保持一致
   + **持续维护中，推荐使用**，还提供了 Swagger 文档的支持。
4. [Flask-Classy](https://pythonhosted.org/Flask-Classy/): 提供Class-Based-View的封装
   + GitHub仓库 [flask-classy](https://github.com/apiguy/flask-classy)
   + PyPI版本到 0.6.10，GitHub的Release版本只剩一个0.5.2
   + 现已**不维护**了，建议使用下面的 Flask-Classful
5. [Flask-Classful](https://flask-classful.readthedocs.io/en/latest/): 从 Flask-Classy 仓库fork而来
   + GitHub地址为 [flask-classful](https://github.com/pallets-eco/flask-classful)
   + PyPI版本只到 0.16.0，没有到正式版，GitHub的Release版本保持一致
   + **持续维护中**，推荐使用，个人用起来很顺手

PS:
> 前面 3 个插件使用风格很相似，感觉学 Flask-RESTful 就行了，不过 Flask-RESTX 提供了Swagger Documentation的支持，这倒是有点吸引力。   
> 后面 2 个插件使用风格相似，个人用起来非常顺手，而且源码就一个py文件，理解起来也容易。


---------
# 身份认证

有关用户身份认证的参考资料：
+ [For a REST API, can I use authentication mechanism provided by flask-login or do I explicitly have to use token based authentication like JWT?](https://stackoverflow.com/questions/65520316/for-a-rest-api-can-i-use-authentication-mechanism-provided-by-flask-login-or-do)
+ [Flask-HttpAuth and Flask-Login](https://stackoverflow.com/questions/26163767/flask-httpauth-and-flask-login)
+ [REST API authentication in Flask](https://medium.com/@anubabajide/rest-api-authentication-in-flask-481518a7479b)
+ [Flask插件系列(九)–HTTP认证](http://www.bjhee.com/flask-ext9.html)
+ 《Flask开发实战》，Chapter 10.3.4

Web开发里有通常有两种身份认证类型：
1. 针对浏览器的Web服务认证
   + 这类Web服务的客户端一般是浏览器，认证过程需要借助浏览器的cookies来实现
   + 此时视图函数一般返回的是渲染后的HTML页面
   + 这种认证一般使用 *Flask-Login* 插件来实现
2. REST-API的服务认证
   + REST-API一般是**无状态**的，不能借助cookies来实现认证
   + 此时视图函数一般返回的是JSON格式的数据，页面显示逻辑交给前端框架实现
   + 这种认证可以使用 *Flask-HttpAuth* 或者 *Flask-JWT-Extended* 插件实现

在REST-API认证中，Flask-HttpAuth 或者 Flask-JWT-Extended 的区别如下：
+ Flask-HttpAuth 只提供了认证的**流程框架**，包含简单用户名/密码认证，token认证等多个方案，但是认证过程中的一些细节，比如token生成，
  token验证，用户提取等具体实现需要我们自己完成，繁琐一点，需要了解JWT的token生成过程，但是可定制化程度高；另外它还提供了一些简单的**用户角色权限管理**功能。     
  > PS: 这个插件很精简，整个就一个不到500行的源文件，可以研究一下。
+ Flask-JWT-Extended 只提供了基于token的认证，在实现了token认证流程的基础上，还提供了token生成和验证的实现，用起来更方便一点，
  但是它**并不提供用户角色权限管理的功能**


---------
# 权限控制

Flask有如下常用的ACL或者RBAC的插件：
+ [Flask-Security](https://pythonhosted.org/Flask-Security/): 2020.4后就没有commit了，**不再维护**，但是历史版本比较多，有正式版
+ [**Flask-Security-Too**](https://flask-security-too.readthedocs.io/en/stable/): **Flask-Security的接替者（3.0.0版本开始），使用比较广泛**。   
  + 这是一个比较重的插件，它会依赖不少其他的Flask-插件，包括下面的Flask-Principal。
  + 这个插件在PyPI上名称为 `Flask-Security`，但是在 conda-forge 里名称是 `flask-security-too`，不过导包时名称都一样。
+ [Flask-Principal](https://pythonhosted.org/Flask-Principal/): 2015年后就没有commit了，没有到正式版。   
  **它的开发者Mattupstate也是Flask-Security的开发者**，这也是为什么它会被Flask-Security使用的原因（即使是在新版本中也是如此）。    
  虽然这个库很久不更新了，但是这个库的设计理念似乎挺好的，而且就一个500行不到的源码文件，可以研究一下。
+ [**Flask-Authorize**](https://flask-authorize.readthedocs.io/en/latest/): **没到正式版**，但是仓库一直有人维护，似乎比较小众
+ [~~Flask-ACL~~](https://mikeboers.github.io/Flask-ACL/): 没有版本信息，没找到GitHub仓库，文档内容很简单
+ [~~Flask-RBAC~~](https://flask-rbac.readthedocs.io/en/latest/): 2020.11后就没有更新版本，但是有commit，没到正式版



------
# 参数验证+序列化插件
这部分的功能只推荐两个库: marshmallow 和 webargs。

至于Pydantic，它和FastAPI的结合比较紧密，和Flask的结合似乎没有那么好。

## marshmallow

marshmallow本身是专门用于序列化/反序列化的库，官方文档 [marshmallow: simplified object serialization](https://marshmallow.readthedocs.io/en/stable/),
GitHub地址 [marshmallow](https://github.com/marshmallow-code/marshmallow).

这个库感觉用起来还可以，挺顺手的。

## webargs

webargs是基于marshmallow提供请求参数校验解析的库，官方文档 [webargs](https://webargs.readthedocs.io/en/latest/index.html), GitHub地址 [webargs](https://github.com/marshmallow-code/webargs).

如果熟悉marshmallow的使用，webargs上手也很快，而且它直接提供了对 Flask, Django等web框架的支持，使用起来也很友好。


------
# Swagger文档插件

目前看到的只有两个相关插件：
+ Flask-RESTX
+ [Flasgger](https://github.com/flasgger/flasgger)

Flasgger的使用教程可以参考如下博客，不过个人感觉使用体验并不好
+ [CSDN: Swagger 介绍（Flask+Flasgger的应用）](https://blog.csdn.net/weixin_44597347/article/details/135135476)
+ [Flask 应用集成 Swagger UI](https://yanbin.blog/flask-integrate-with-swagger-ui/)
+ [Flasgger使用心得](https://changsiyuan.github.io/2017/05/20/2017-5-20-flasgger/)

> 个人感觉当前在Flask里实现对Swagger的支持，并没有好用的方案。

