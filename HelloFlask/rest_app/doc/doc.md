
RESTful风格 在 Flask 中的实现插件主要有如下几个：
1. [Flask-RESTful](https://flask-restful.readthedocs.io/en/latest/index.html)
2. [Flask-RESTPlus](https://flask-restplus.readthedocs.io/en/latest/)
3. [Flask-RESTX](https://flask-restx.readthedocs.io/en/latest/)
其中 Flask-RESTful 是最早的，也是使用最广泛的；Flask-RESTPlus 是后来开发的，但是现在已经不维护了，Flask-RESTX 是从 Flask-RESTPlus fork 而来。

这 3 个插件的使用风格都很相似，我感觉学 Flask-RESTful 就行了。


此外，还有一个 [Flask-classful](https://flask-classful.readthedocs.io/en/latest/#) 插件，[GitHub地址](https://github.com/pallets-eco/flask-classful)，
我觉得用起来非常顺手，而且源码就一个py文件，理解起来也容易。

这个插件是从 Flask-classy项目 fork而来，因为Flask-classy项目似乎没人维护了。