
# RESTful扩展

RESTful风格 在 Flask 中的扩展实现主要有如下几个：
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
> 前面 3 个扩展使用风格很相似，感觉学 Flask-RESTful 就行了，不过 Flask-RESTX 提供了Swagger Documentation的支持，这倒是有点吸引力。   
> 后面 2 个扩展使用风格相似，个人用起来非常顺手，而且源码就一个py文件，理解起来也容易。

------
# 参数验证+序列化扩展
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
# Swagger文档支持扩展

目前看到的只有两个相关扩展：
+ Flask-RESTX
+ [Flasgger](https://github.com/flasgger/flasgger)

Flasgger的使用教程可以参考如下博客，不过个人感觉使用体验并不好
+ [CSDN: Swagger 介绍（Flask+Flasgger的应用）](https://blog.csdn.net/weixin_44597347/article/details/135135476)
+ [Flask 应用集成 Swagger UI](https://yanbin.blog/flask-integrate-with-swagger-ui/)
+ [Flasgger使用心得](https://changsiyuan.github.io/2017/05/20/2017-5-20-flasgger/)

> 个人感觉当前在Flask里实现对Swagger的支持，并没有好用的方案。



