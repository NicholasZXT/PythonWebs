
# 身份认证

有关用户身份认证的参考资料：
+ [For a REST API, can I use authentication mechanism provided by flask-login or do I explicitly have to use token based authentication like JWT?](https://stackoverflow.com/questions/65520316/for-a-rest-api-can-i-use-authentication-mechanism-provided-by-flask-login-or-do)
+ [Flask-HttpAuth and Flask-Login](https://stackoverflow.com/questions/26163767/flask-httpauth-and-flask-login)
+ [REST API authentication in Flask](https://medium.com/@anubabajide/rest-api-authentication-in-flask-481518a7479b)
+ [Flask扩展系列(九)–HTTP认证](http://www.bjhee.com/flask-ext9.html)
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
  > PS: 这个扩展很精简，整个就一个不到500行的源文件，可以研究一下。
+ Flask-JWT-Extended 只提供了基于token的认证，在实现了token认证流程的基础上，还提供了token生成和验证的实现，用起来更方便一点，
  但是它**并不提供用户角色权限管理的功能**

-------
# 权限控制

Flask有如下常用的ACL或者RBAC的扩展：
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

