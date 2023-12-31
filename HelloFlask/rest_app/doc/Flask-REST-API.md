
RESTful风格 在 Flask 中的实现插件主要有如下几个：
1. [Flask-RESTful](https://flask-restful.readthedocs.io/en/latest/index.html)：最早的Flask-REST项目，使用最广泛
2. [~~Flask-RESTPlus~~](https://flask-restplus.readthedocs.io/en/latest/)：后来开发，但是现在已经**不维护了**
3. [Flask-RESTX](https://flask-restx.readthedocs.io/en/latest/)：从 Flask-RESTPlus 仓库 fork 而来
4. [~~Flask-Classy~~](https://pythonhosted.org/Flask-Classy/)：现已**不维护**了
5. [Flask-Classful](https://flask-classful.readthedocs.io/en/latest/)，[GitHub地址](https://github.com/pallets-eco/flask-classful)：从 Flask-Classy 仓库fork而来

前面 3 个插件使用风格很相似，感觉学 Flask-RESTful 就行了，不过 Flask-RESTX 提供了Swagger Documentation的支持，这倒是有点吸引力。  
后面 2 个插件使用风格相似，个人用起来非常顺手，而且源码就一个py文件，理解起来也容易。