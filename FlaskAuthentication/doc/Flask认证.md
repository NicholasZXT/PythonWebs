[TOC]

参考资料：
+ [For a REST API, can I use authentication mechanism provided by flask-login or do I explicitly have to use token based authentication like JWT?](https://stackoverflow.com/questions/65520316/for-a-rest-api-can-i-use-authentication-mechanism-provided-by-flask-login-or-do)
+ [Flask-HttpAuth and Flask-Login](https://stackoverflow.com/questions/26163767/flask-httpauth-and-flask-login)
+ [REST API authentication in Flask](https://medium.com/@anubabajide/rest-api-authentication-in-flask-481518a7479b)
+ [Flask扩展系列(九)–HTTP认证](http://www.bjhee.com/flask-ext9.html)
+ 《Flask开发实战》，Chapter 10.3.4

Web开发里有通常有两种认证类型：
1. 针对浏览器的Web服务认证
   + 这类Web服务的客户端一般是浏览器，认证过程需要借助浏览器的cookies来实现
   + 此时视图函数一般返回的是渲染后的HTML页面
   + 这种认证一般使用 *Flask-login* 插件来实现
2. REST-API的服务认证
   + REST-API一般是**无状态**的，不能借助cookies来实现认证
   + 此时视图函数一般返回的是JSON格式的数据，页面显示逻辑交给前端框架实现
   + 这种认证可以使用 *Flask-HttpAuth* 插件来实现

