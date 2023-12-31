[TOC]


# Tips

个人练习Django的一些感受：
+ Django提供了开箱即用的 Admin 模块和对应的管理界面，还提供了 User 类和对应的认证机制，方便快速开发
+ Django整个框架和它底层ORM的耦合程度比较高，大部分操作都依赖于底层的ORM，特别是 Admin 界面和用户认证，这部分封装的比较深
+ 相比于Flask，Django比较规范，不过也缺少了自由度，比如在Flask中，我可以自由操作数据库，用或者不用ORM都可以，特别是快速开发或者呈现数据分析结果的时候

> 我对于Django的 MVC（或者MVT） 开发兴趣不大，暂时不研究后端同时负责获取数据 + 设计模板 + 注入数据进行渲染的这些操作。   
> 个人更倾向于后端负责获取数据，处理数据，然后返回指定的数据结构——也就是**前后端分离的模式**，这种场景下，应该关注的是 *Django REST Framework* 或者 * Django Ninjia* 这些扩展。

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

# 功能深入

## 用户认证+鉴权系统

参考文档：

+ 官方文档 [User authentication in Django](https://docs.djangoproject.com/en/4.2/topics/auth/)
+ 官方API文档 [`django.contrib.auth`](https://docs.djangoproject.com/en/4.2/ref/contrib/auth/)
+ [Django权限详解](https://pythondjango.cn/django/advanced/8-permissions/)

Django中的用户认证和鉴权系统联系的比较紧密，所以就一起介绍了。

这部分主要涉及到`django.contrib.auth.models`包中如下的3个对象，均为是`django.db.models.Model`的子类：

+ `Permission`，记录权限信息，主要字段如下：
  + `name`：权限的描述
  + `codename`：权限描述简写
  + `content_type `：权限对应的表模型的编号
+ `Group`，记录用户组信息，主要字段如下：
  + `name`：组名称
  + `permissions`：**多对多字段**，记录了组和权限的映射关系
+ `User`，记录了用户信息和权限信息
  + `name`：用户名
  + `first_name`，`last_name`，用户姓名，可以为空
  + `email`：邮件地址
  + `password`：密码哈希值
  + `is_active`：是否为活跃用户
  + `is_staff`：是否为员工，也就是能否访问Admin信息
  + `is_superuser`：是否为超级管理员，可以对`User`表进行增删查改
  + `groups`：**多对多字段**，用户所属的组信息
  + `user_permissions`：**多对多字段**，用户所具有的权限信息

整体框架大致如下：

1. 在`settings.py`的`INSTALLED_APPS`里启用`django.contrib.auth  `模块之后，

   + 后续每次对所有的App执行`makemigration`时，会扫描所有App下的数据模型，为每个模型生成对应的`Permission`记录，存放在**`auth_permission`**表中。

   + 对应于增删查改的4种权限，每个模型有4条记录，各个记录的`codename`为（假设模型为`Article`）：`add_article`,`delete_article`,`view_article`,`change_article`
   + 应用到具体的App上时，对应的权限名称就是：`{app_name}.{codename}`，比如blog应用的`Article`模型的权限名称就是`blog.add_article`,`blog.view_article`等

2. 后续增加用户组时，增加一个`Group`对象来记录该组的信息

   + 组的基本信息放在**`auth_group`**表中，里面只有`id`，`name`字段
   + `permissions`是一个多对多字段，它的值是单独存放在**`auth_group_permissions`**表中，存放该组和权限的多对多关系

3. 管理用户虽然是操作的`User`模型，但是底层有如下表：

   + 用户的基本信息管理存放在**`auth_user`**表中
   + `group`是一个多对多字段，对应的是**`auth_user_groups`**表，里面存放用户和组的映射关系
   + `permissions`也是多对多字段，对应的是**`auth_user_user_permissions`**表

上面的这5张表其实就是`django.contrib.auth  `模块所使用的全部数据模型。

实际使用中，`Permission`对应的权限模型是不需要我们来手动生成或者管理的，而且一般开发中，我们几乎不会直接操作`Permission`模型，主要的操作对象是用户和用户组，因此下面就不讨论`Permission`的使用。


### 用户和权限管理

+ 创建超级用户，只能使用如下的命令行：

```shell
$ python manage.py createsuperuser --username=joe --email=joe@example.com
# 如果没有指定 --username 或者 --email，那么就会提示输入
# 接下来会提示输入用户密码
```

+ 创建普通用户，有两种方式：

  1. 在Admin界面创建用户
  2. 在代码中创建用户

  ```shell
  from django.contrib.auth.models import User
  user = User.objects.create_user("john", "lennon@thebeatles.com", "johnpassword")
  user.last_name = "Lennon"
  user.save()
  ```

+ 用户组、用户权限的代码管理方式

```python
myuser.groups.set([group_list])
myuser.groups.add(group, group, ...)
myuser.groups.remove(group, group, ...)
myuser.groups.clear()

myuser.user_permissions.set([permission_list])
myuser.user_permissions.add(permission, permission, ...)
myuser.user_permissions.remove(permission, permission, ...)
myuser.user_permissions.clear()

# 用户组的权限管理
mygroup.permissions = [permission1, permission2, ...]
mygroup.permissions.add(permission1, permission2, ...)
mygroup.permissions.remove(permission1, permission2, ...)
mygroup.permissions.clear()
```

+ 查看用户权限

```python
# 查看用户的所有权限
myuser.get_group_permissions()
myuser.get_all_permissions()

# 查看用户是否有操作某个App指定数据的权限，使用 .has_perm() 方法
myuser.has_perm('blog.add_article')
```



### 用户认证+鉴权

+ 基础用户认证，使用`authenticate()`函数——这是比较底层的方式，通常不会直接使用

```python
from django.contrib.auth import authenticate
user = authenticate(username="john", password="secret")
# 或者传入一个请求对象，这个是可选的
# user = authenticate(request=request, username="john", password="secret")
# 认证成功，则会返回对应用户的 User 对象
# 认证失败，返回None
```

+ 使用`permission_required`装饰器，作用于视图函数

```python
from django.contrib.auth.decorators import permission_required

# 括号里的是权限名称
@permission_required('polls.can_vote')
def my_view(request):
    pass
```

+ 使用`PermissionRequiredMixin`工具类，作用于类

```python
from django.views import View
from django.contrib.auth.mixins import PermissionRequiredMixin

class MyView(View, PermissionRequiredMixin):
    permission_required = 'polls.can_vote'
    # Or multiple of permissions:
    permission_required = ('polls.can_open', 'polls.can_edit')
    ...
```

+ 使用`method_decorator`装饰器，作用于类——略

> 注意，上面的鉴权过程，都是针对整个数据模型的，并不能精细到数据模型的某一行

+ 要想控制数据模型里具体一行的权限有如下两种方式：
  1. 使用第三方扩展`django-guardian`
  2. 自定义对应的`ModelAdmin`类中的`has_view_permission()`，`has_add_permission()`等方法