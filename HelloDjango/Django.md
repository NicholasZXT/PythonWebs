[TOC]


# Tips

个人练习Django的一些感受：
+ Django提供了开箱即用的 Admin 模块和对应的管理界面，还提供了 User 类和对应的认证机制，方便快速开发
+ Django整个框架和它底层ORM的耦合程度比较高，大部分操作都依赖于底层的ORM，特别是 Admin 界面和用户认证，这部分封装的比较深
+ 相比于Flask，Django比较规范，不过也缺少了自由度，比如在Flask中，我可以自由操作数据库，用或者不用ORM都可以，特别是快速开发的时候，不需要每次表变动，都需要去更新ORM里定义的Models

> 我对于Django的 MVC（或者MVT） 开发兴趣不大，暂时不研究后端同时负责获取数据 + 设计模板 + 注入数据进行渲染的这些操作。   
> 个人更倾向于后端只负责获取数据，处理数据，然后返回指定的数据结构——也就是**前后端分离的模式**，这种场景下，应该关注的是 *Django REST Framework* 这个扩展。

---

# 基础

> 此练习项目来自于胡阳《Django企业开发实战》里的typeidea博客.

+ 初始化项目   
使用`django-admin startproject <proj_name> [directory]` 命令生成项目。   
  + 如果只指定`proj_name`，则会在当前目录下，创建一个 `proj_name` 的文件夹作为项目**根目录**，其中生成如下内容：
    + `manage.py`文件，用于管理项目
    + `proj_name`**子文件夹**，存放具体的项目管理App
  + 如果同时指定了`directory`，则会使用指定的目录作为**项目根目录**，在里面创建`manage.py`和`proj_name`**子文件夹**
  + 外层的`proj_name`文件夹是项目根目录——**它的名称可以随便改**，里层的`proj_name`子文件夹名称会被作为整个项目package后续被导入的名称，不能随便修改
  + `proj_name`子文件夹虽然也是一个App，但是它的作用是管理整个项目的配置，所以通常不会在这个目录下生成 models 和 views，其中通常有如下内容：
    + `settings.py`：存放整个项目的配置
    + `urls.py`：存放项目级别的URL映射配置，最终所有的URL映射都要在此引入汇总
    + `asgi.py`：异步Web服务器的入口文件
    + `wsgi.py`：同步Web服务器的入口文件

+ 创建应用
使用 `django-admin startapp <app_name> [directory]` 命令创建一个新的App及对应的目录。  
  + 应用目录里面，没有`settings.py`, `wsgi.py`, `asgi.py`等文件，这些文件只有上面创建项目时，项目的管理App目录里才有
  + 应用目录里，主要有如下的文件/文件夹：
    + `admin.py`，用于设置当前App的后台管理功能
    + `apps.py`，当前App的配置信息，在Django版本后自动生成，一般情况下无需更改
    + `models.py`，每个应用的数据模型定义，ORM层
    + `views.py`，每个应用各自的视图函数
    + `migrations`文件夹，数据库迁移生成的文件
    + `tests.py`，测试相关文件
  + 应用目录里，也可以配置单独的URL映射，也就是**手动生成一个`urls.py`文件**，然后在根路由文件`<proj_name>.urls.py`里引入即可。

---

# Django REST Framework (DRF)

## 安装

```shell
# pip
pip install djangorestframework
# conda
conda install -c conda-forge djangorestframework
```
