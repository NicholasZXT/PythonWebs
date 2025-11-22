[TOC]

个人练习Django的一些感受：
+ Django提供了开箱即用的 Admin 模块和对应的管理界面，还提供了 User 类和对应的认证机制，方便快速开发
+ Django整个框架和它底层ORM的耦合程度比较高，大部分操作都依赖于底层的ORM，特别是 Admin 界面和用户认证，这部分封装的比较深
+ 相比于Flask，Django比较规范，不过也缺少了自由度，比如在Flask中，可以自由操作数据库，用或者不用ORM都可以，特别是快速开发或者呈现数据分析结果的时候

# 版本概览

| 版本                 | 发布时间    | Python 支持    | LTS（长期支持）          | 流行度（2025年）           |
|--------------------|---------|--------------|--------------------|----------------------|
| **Django 1.11**    | 2017-04 | 2.7, 3.4–3.6 | ✅（已结束支持）           | 低（仅遗留系统）             |
| **Django 2.0**     | 2017-12 | ≥3.4         | ❌                  | 中低                   |
| **Django 2.2**     | 2019-04 | ≥3.5         | ✅（支持至 2022-04）     | 中（逐步淘汰）              |
| **Django 3.0**     | 2019-12 | ≥3.6         | ❌                  | 中                    |
| **Django 3.2**     | 2021-04 | ≥3.6         | ✅（支持至 **2024-04**） | **高（过渡期主流）**         |
| **Django 4.0**     | 2021-12 | ≥3.8         | ❌                  | 中高                   |
| **Django 4.1**     | 2022-08 | ≥3.8         | ❌                  | —                    |
| **Django 4.2**     | 2023-04 | ≥3.8         | ✅（支持至 **2026-04**） | **⭐ 最推荐的 LTS（当前主流）** |
| **Django 5.0**     | 2023-12 | ≥3.10        | ❌                  | 快速上升（新项目首选）          |
| **Django 5.1**     | 2024-08 | ≥3.10        | ❌                  | 新兴                   |
| **Django 5.2**（预计） | 2025-04 | ≥3.10        | ✅（预计）              | 即将发布                 |

异步支持演进：

| 版本                    | 异步支持状态                               | 关键限制                                                        |
|-----------------------|--------------------------------------|-------------------------------------------------------------|
| **Django 3.0 (2019)** | ✅ 初步支持 ASGI + 异步视图                   | ❌ ORM 完全同步，无法在 async 视图中直接查数据库（需 `sync_to_async` 包装）        |
| **Django 3.1–3.2**    | ⚙️ 改进 ASGI 和测试客户端                    | ❌ ORM 仍阻塞；异步生态碎片化                                           |
| **Django 4.0–4.2**    | 🛠️ 增强中间件/信号异步兼容性                    | ❌ ORM 仍未原生异步；开发者需手动处理同步/异步边界                                |
| **Django 5.0 (2023)** | ✅ **全面拥抱异步：视图 + ORM（实验性）+ 中间件 + 测试** | ⚠️ 异步 ORM 为**实验性**，但已可直接使用 `await Model.objects.aget()` 等方法 |


当前（2025年）最推荐版本：

- **长期维护项目**：**Django 4.2 LTS**
- **新项目**：**Django 5.0 或 5.1**




-------
# 命令行工具

Django 提供了 **两类命令行工具**：

- **`django-admin`**：全局命令行工具（无需项目上下文即可运行）
- **`manage.py`**：项目级命令行工具（自动配置 Django 环境）

此外，Django 还支持通过 **自定义管理命令** 和 **第三方扩展**（如 `django-extensions`）扩展命令行能力。

**日常开发中几乎总是使用 `manage.py` 而非 `django-admin`**，因为 `manage.py` 自动处理了环境配置。



## django-admin

全局命令行工具，用途：

- 创建新项目
- 在未配置 `DJANGO_SETTINGS_MODULE` 的环境中执行部分操作
- 调试或脚本化部署流程

常用命令如下：

| 命令                                                   | 说明                              | 示例                               |
| ------------------------------------------------------ | --------------------------------- | ---------------------------------- |
| `django-admin version`                                 | 查看 Django 版本                  | `django-admin version` → `5.0.6`   |
| `django-admin startproject <name>`                     | 创建新 Django 项目                | `django-admin startproject mysite` |
| `django-admin startapp <name>`                         | 创建新应用（不推荐单独使用）      | `django-admin startapp blog`       |
| `django-admin runserver --settings=myproject.settings` | 启动服务器（需显式指定 settings） | ⚠️ 不如 `manage.py` 方便            |
| `django-admin shell --settings=...`                    | 启动 shell（需指定 settings）     |                                    |

- `django-admin startproject`：

```shell
> django-admin startproject -h
usage: django-admin startproject [-h] 
    [--template TEMPLATE] [--extension EXTENSIONS] 
    [--name FILES] [--exclude [EXCLUDE]] [--version] [-v {0,1,2,3}] 
    [--settings SETTINGS] [--pythonpath PYTHONPATH] [--traceback] 
    [--no-color] [--force-color]
    name [directory]

Creates a Django project directory structure for the given project name in the current directory or optionally in the given directory.

positional arguments:
  name                  Name of the application or project.
  directory             Optional destination directory
```

- `django-admin startapp`

```shell
> django-admin startapp -h
usage: django-admin startapp [-h] 
    [--template TEMPLATE] [--extension EXTENSIONS] 
    [--name FILES] [--exclude [EXCLUDE]] [--version] [-v {0,1,2,3}] 
    [--settings SETTINGS]  [--pythonpath PYTHONPATH] [--traceback] [--no-color] [--force-color]
    name [directory]

Creates a Django app directory structure for the given app name in the current directory or optionally in the given directory.

positional arguments:
  name                  Name of the application or project.
  directory             Optional destination directory
```



## manage.py

项目级命令行工具（推荐使用），此文件由 `django-admin startproject` 创建。

此脚本会自动设置`DJANGO_SETTINGS_MODULE`，所有 Django 内置命令均可直接使用。

**所有 `django-admin` 支持的命令，`manage.py` 都支持，且更方便**。

常用命令如下：

- 基础命令：

| 命令                                   | 说明                                                         | 示例                                      |
| -------------------------------------- | ------------------------------------------------------------ | ----------------------------------------- |
| `python manage.py runserver [ip:port]` | 启动开发服务器（仅用于开发）                                 | `python manage.py runserver 0.0.0.0:8000` |
| `python manage.py shell`               | 进入 Django 增强版 Python shell（自动加载模型）              | `python manage.py shell`                  |
| `python manage.py shell_plus`          | （需安装 `django-extensions`）更强大的 shell，自动导入所有模型 | `pip install django-extensions` 后可用    |
| `python manage.py help [command]`      | 查看命令帮助                                                 | `python manage.py help migrate`           |

- 数据库管理

| 命令                                                    | 说明                                   | 典型场景                |
| ------------------------------------------------------- | -------------------------------------- | ----------------------- |
| `python manage.py makemigrations [app_label]`           | 根据模型变更生成迁移文件               | 修改 `models.py` 后执行 |
| `python manage.py migrate [app_label] [migration_name]` | 应用迁移（创建/更新表结构）            | 首次部署或更新数据库时  |
| `python manage.py showmigrations`                       | 显示所有迁移状态（✓ 表示已应用）       | 检查迁移是否遗漏        |
| `python manage.py sqlmigrate app migration_name`        | 查看某次迁移对应的 SQL 语句            | 调试或审查 SQL          |
| `python manage.py dbshell`                              | 进入数据库命令行（需安装对应客户端）   | 手动执行 SQL 查询       |
| `python manage.py flush`                                | 清空数据库（保留表结构，删除所有数据） | 开发环境重置数据        |

- 用户与权限

| 命令                                         | 说明                                       |
| -------------------------------------------- | ------------------------------------------ |
| `python manage.py createsuperuser`           | 创建超级管理员用户（用于访问 Admin）       |
| `python manage.py changepassword <username>` | 修改指定用户的密码                         |
| `python manage.py createsuperuser --noinput` | 非交互式创建（配合环境变量使用，如 CI/CD） |

- 检查与诊断

| 命令                              | 说明                                     |
| --------------------------------- | ---------------------------------------- |
| `python manage.py check`          | 检查项目配置错误（如模型、设置问题）     |
| `python manage.py check --deploy` | 检查生产环境潜在问题（安全、性能等）     |
| `python manage.py diffsettings`   | 显示当前生效的 settings 与默认值的差异   |
| `python manage.py inspectdb`      | 从现有数据库反向生成模型（遗留系统集成） |



-------
# 项目初始化

## 通用模板

Django项目结构通用模板如下：

```text
myproject/                     # 项目根目录（通常与 Git 仓库同名）
│
├── manage.py                  # 命令行工具入口（如 runserver, migrate）
│
├── requirements/              # 【可选但推荐】依赖管理（按环境拆分）
│   ├── base.txt               # 基础依赖（如 Django, requests）
│   ├── local.txt              # 开发环境（+ debug_toolbar 等）
│   ├── production.txt         # 生产环境（+ gunicorn, psycopg2 等）
│   └── testing.txt            # 测试环境
│
├── myproject/                 # **Django 项目包（由 django-admin startproject 生成）**
│   ├── __init__.py
│   ├── settings/              # 【推荐】拆分 settings（替代单一 settings.py）
│   │   ├── __init__.py
│   │   ├── base.py            # 通用配置
│   │   ├── local.py           # 开发环境（DEBUG=True, SQLite 等）
│   │   └── production.py      # 生产环境（安全设置、数据库等）
│   │
│   ├── urls.py                # 项目级 URL 路由（include 各 app 的 urls）
│   ├── wsgi.py                # WSGI 部署入口（用于 Gunicorn/uWSGI）
│   └── asgi.py                # ASGI 入口（用于异步支持，如 Daphne）
│
├── apps/                      # 【推荐】集中存放自定义应用（避免与项目同级混乱）
│   ├── __init__.py
│   ├── users/                 # 示例 App：用户管理
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py 或 views/
│   │   ├── serializers.py     # 若用 DRF
│   │   ├── admin.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   └── blog/                  # 另一个 App：博客
│       └── ...
│
├── static/                    # 全局静态文件（CSS, JS, images）
│   └── css/
│
├── media/                     # 用户上传文件（开发时使用，生产通常用 S3/CDN）
│
├── templates/                 # 全局模板目录（各 app 也可有自己的 templates）
│   └── base.html
│
├── locale/                    # 国际化翻译文件（.po/.mo）
│
├── .env                       # 【推荐】环境变量（配合 python-decouple 或 dotenv）
├── .gitignore
├── README.md
├── Dockerfile                 # 【可选】容器化部署
├── docker-compose.yml
└── pytest.ini 或 setup.cfg    # 测试配置
```



## 初始化项目

> 此练习项目来自于胡阳《Django企业开发实战》里的typeidea博客.

（1）初始化项目

使用`django-admin startproject <proj_name> [directory]` 命令生成项目。   

+ 如果只指定`proj_name`，则会在当前目录下，创建一个 `proj_name` 的文件夹作为项目**根目录**，其中生成如下内容：
  + `manage.py`文件，用于管理项目
  + `proj_name`**子文件夹**，存放具体的项目管理App
+ 如果同时指定了`directory`，则会使用指定的目录作为**项目根目录**，在里面创建`manage.py`和`proj_name`**子文件夹**
+ 外层的`proj_name`文件夹是项目根目录——**它的名称可以随便改**，里层的`proj_name`子文件夹名称会被作为整个项目package后续被导入的名称，不能随便修改
+ `proj_name`子文件夹虽然也是一个App，但是它的作用是管理整个项目的配置，所以通常不会在这个目录下生成 models 和 views，其中通常有如下内容：
  + `settings.py`：存放整个项目的配置——这个建议改成packages，内部区分不同环境的配置文件
  + `urls.py`：存放项目级别的URL映射配置，最终所有的URL映射都要在此引入汇总
  + `asgi.py`：异步Web服务器的入口文件
  + `wsgi.py`：同步Web服务器的入口文件

（2）创建应用

使用 `django-admin startapp <app_name> [directory]` 命令创建一个新的App及对应的目录。  

+ 此命令可以在任意目录下执行：
  + **不依赖`manage.py`**，但是建议在`manager.py`所在的目录里执行。
  + 执行后，默认在当前目录下生成一个`app_name`的目录，除非指定了`directory`参数。
  + 生成的APP目录本质是一个Python包，可以任意移动，但是要被某个Django项目识别，则需要在该项目的`settings.py`的`INSTALLED_APPS`列表里进行注册。

+ 应用目录里面，没有`settings.py`, `wsgi.py`, `asgi.py`等文件，这些文件只有上面创建项目时，项目的管理App目录里才有
+ 应用目录里，主要有如下的文件/文件夹：
  + `apps.py`，当前App的配置信息，在Django版本后自动生成，一般情况下无需更改
  + `admin.py`，用于设置当前App的后台管理功能
  + `models.py`，每个应用的数据模型定义，ORM层
  + `views.py`，每个应用各自的视图函数
  + `migrations`文件夹，数据库迁移生成的文件
  + `tests.py`，测试相关文件
+ 应用目录里，也可以配置单独的URL映射，也就是**手动生成一个`urls.py`文件**，然后在根路由文件`<proj_name>.urls.py`里引入即可。



## 初始化数据库

对于Django的新项目，初次使用之前，需要为一些内置组件在数据库里初始化一些表，默认下在`settings.py`里引用了如下组件：

```python
INSTALLED_APPS = [
    'django.contrib.admin',      # ← Admin 后台
    'django.contrib.auth',       # ← 用户认证（User, Group, Permission）
    'django.contrib.contenttypes', # ← 内容类型框架（支持 GenericForeignKey）
    'django.contrib.sessions',   # ← 会话管理
    'django.contrib.messages',   # ← 消息框架
    'django.contrib.staticfiles', # ← 静态文件（无数据库表）
    # ...（你的自定义 app）
]
```

其中前5个组件会创建一些表：

| 表名（默认）          | 所属 App            | 用途                                                         |
| --------------------- | ------------------- | ------------------------------------------------------------ |
| `django_admin_log`    | `admin`             | **Admin 操作日志**（谁在后台做了什么）                       |
| `auth_user`           | `auth`              | 用户账户（Admin 登录用）                                     |
| `auth_group`          | `auth`              | 用户组                                                       |
| `auth_permission`     | `auth`              | 权限系统                                                     |
| `django_content_type` | `contenttypes`      | 记录项目中所有模型的元信息（如 `app_label="auth", model="user"`） |
| `django_session`      | `sessions`          | 存储用户会话（默认数据库后端）                               |
| `django_site`         | `sites`（如果启用） | 多站点支持（默认未启用）                                     |

**数据库初始化**操作如下：

（1）生成初始迁移文件：为所有包含Models的App（包含自带App）生成初始迁移文件：

```shell
python manage.py makemigrations
```

各个App生成的迁移文件位于各自的 `migrations/` 目录，但是**自带App不需要生成初次迁移文件，因为内置在框架模块里了**。

（2）应用迁移（创建表结构）

```shell
python manage.py migrate
```

（3）创建超级管理员

```shell
python manage.py createsuperuser
```

按提示输入信息：

- **Username**（用户名）：例如 `admin`
- **Email address**（邮箱，可选）：例如 `admin@example.com`
- **Password**（密码）：输入两次，注意终端不会显示你输入的内容（出于安全考虑）

如果提示密码太简单，可以在`settings.py`里，注释掉`AUTH_PASSWORD_VALIDATORS`里的部分插件。

> 如果忘记了管理员密码，有两种解决办法：
>
> （1）再次运行`python manage.py createsuperuser`，创建一个新的管理账号，不能和原来的同名
>
> （2）通过 Django shell 重置现有管理员密码（适用于生产或开发环境
>
> - 使用`python manage.py shell`进入Django shell
> - 执行下列Python代码进行密码重置（假设管理员名称为`admin`）
>
> ```python
> from django.contrib.auth import get_user_model
> 
> User = get_user_model()
> user = User.objects.get(username='admin')  # 或用 email 等其他字段查找
> user.set_password('newpassword123')
> user.save()
> ```

（4）后续如果修改了Models，则需要执行新的迁移操作：

```shell
python manage.py makemigrations
python manage.py migrate
```



**其他技巧：**

```shell
# 查看迁移状态
# 显示所有 app 的迁移应用情况（✓ 表示已应用）
python manage.py showmigrations

# 查看 SQL 语句（调试用）
python manage.py sqlmigrate books 0002

# 回滚迁移（谨慎！）
python manage.py migrate books 0001  # 回退到 0001
python manage.py migrate books zero  # 完全撤销该 app 所有迁移
```





------

# ORM

## Model定义

### 常用字段类型

| 字段类型                                    | 用途                            |
| ------------------------------------------- | ------------------------------- |
| `CharField`                                 | 短字符串（必须设 `max_length`） |
| `TextField`                                 | 长文本                          |
| `IntegerField` / `BigIntegerField`          | 整数                            |
| `DecimalField`                              | 精确小数（金融类）              |
| `FloatField`                                | 浮点数（不精确）                |
| `BooleanField`                              | 布尔值                          |
| `DateField` / `DateTimeField` / `TimeField` | 日期/时间相关                   |
| `EmailField` / `URLField` / `SlugField`     | 特殊格式字符串（自带验证）      |
| `ForeignKey`                                | 外键（多对一）                  |
| `OneToOneField`                             | 一对一                          |
| `ManyToManyField`                           | 多对多                          |

### 常见字段选项

- `max_length`：最大长度（CharField 必填）
- `blank=True`：表单验证允许为空（前端）
- `null=True`：数据库允许 NULL（慎用于字符串字段）
- `default=...`：默认值
- `unique=True`：唯一约束
- `verbose_name`：人类可读名称
- `help_text`：表单提示
- `choices`：枚举选项
- `on_delete`：外键删除行为（如 `CASCADE`, `SET_NULL`）

### 常用 Meta 选项

| 选项                                   | 说明                                               |
| -------------------------------------- | -------------------------------------------------- |
| `db_table`                             | 自定义表名                                         |
| `db_table_comment`                     | 表注释                                             |
| `db_tablespace`                        | 表名空间                                           |
| `verbose_name` / `verbose_name_plural` | 显示名称                                           |
| `ordering`                             | 默认排序                                           |
| `unique_together`                      | 联合唯一（Django 5.1 起推荐用 `UniqueConstraint`） |
| `indexes`                              | 自定义数据库索引                                   |
| `permissions`                          | 自定义权限                                         |
| `abstract = True`                      | 抽象基类（不创建表）                               |



### 综合示例

```python
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

class BlogPost(models.Model):
    """
    博客文章模型示例，涵盖常用字段类型、字段选项和 Meta 配置。
    """
    # ====== Meta 选项配置 ======
    class Meta:
        # 数据库表名（默认是 app_label_modelname，如 blog_blogpost）
        db_table = 'blog_posts'
        # 在 Admin 或 ORM 查询中默认排序方式
        ordering = ['-created_at']  # 按创建时间倒序（最新在前）
        # 单数和复数显示名称（用于 Django Admin 等界面）
        verbose_name = "博客文章"
        verbose_name_plural = "博客文章"  # 中文通常单复数相同
        # 联合唯一约束：标题 + 作者不能重复
        unique_together = ('title', 'author')
        # 添加数据库索引（提升查询性能）
        indexes = [
            models.Index(fields=['status', '-created_at'], name='status_created_idx'),
        ]
        # 权限控制（自定义权限，可在 Admin 中分配）
        permissions = [
            ("can_publish_post", "可以发布文章"),
            ("can_view_unpublished", "可以查看未发布文章"),
        ]
 

    # ====== 常用字段类型及配置项 ======
    # CharField：用于短文本，必须指定 max_length
    title = models.CharField(
        max_length=200,
        verbose_name="标题",          # 在 Admin 或表单中显示的名称
        help_text="请输入文章标题",     # 表单中的提示文本
        unique=True                   # 唯一约束：不允许重复标题
    )
    # TextField：用于长文本，不限长度（数据库层面可能有限制）
    content = models.TextField(
        verbose_name="内容",
        blank=True,                   # 允许表单为空（前端可不填）
        null=False                    # 数据库中不允许为 NULL（默认行为）
    )
    # BooleanField：布尔值（True/False）
    is_published = models.BooleanField(
        default=False,
        verbose_name="是否发布"
    )
    # IntegerField：整数
    view_count = models.IntegerField(
        default=0,
        verbose_name="浏览量"
    )
    # DecimalField：用于精确小数（如价格），需指定 max_digits 和 decimal_places
    rating = models.DecimalField(
        max_digits=3,                 # 最多3位数字（包括小数部分）
        decimal_places=2,             # 小数点后2位，如 4.95
        default=0.00,
        verbose_name="评分"
    )
    # DateTimeField：日期+时间
    created_at = models.DateTimeField(
        auto_now_add=True,            # 创建时自动设为当前时间，之后不可改
        verbose_name="创建时间"
    )
    updated_at = models.DateTimeField(
        auto_now=True,                # 每次 save() 时自动更新为当前时间
        verbose_name="最后修改时间"
    )
    # DateField：仅日期
    publish_date = models.DateField(
        null=True,                    # 允许数据库为 NULL（未发布时可为空）
        blank=True,                   # 表单可不填
        verbose_name="发布日期"
    )
    # EmailField：邮箱（本质是 CharField + 邮箱格式验证）
    contact_email = models.EmailField(
        blank=True,
        verbose_name="联系邮箱"
    )
    # URLField：URL（带格式验证）
    source_url = models.URLField(
        blank=True,
        verbose_name="来源链接"
    )
    # ForeignKey：外键（多对一）
    author = models.ForeignKey(
        User,                         # 关联到内置 User 模型
        on_delete=models.CASCADE,     # 用户删除时，级联删除其所有文章
        verbose_name="作者"
    )
    # SlugField：用于生成友好 URL（如 /post/my-first-post/）
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,                   # 可在保存时通过信号或重写 save() 自动生成
        verbose_name="URL 标识符"
    )
    # Choices 枚举字段（配合 CharField 使用）
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('published', '已发布'),
        ('archived', '已归档'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="状态"
    )

    # ====== 模型方法（可选但推荐） ======
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """返回该对象的详情页 URL（常用于 Admin 或模板跳转）"""
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """重写 save 方法，可在此自动生成 slug 等逻辑"""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
```



## QuerySet

前置条件：

```python
# models.py 中已定义 BlogPost 和 User 关联
from myapp.models import BlogPost
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
```

### 基础查询

```python
# 获取所有文章（惰性求值，不立即执行 SQL）
all_posts = BlogPost.objects.all()

# 获取单个对象（必须唯一，否则抛异常）
post = BlogPost.objects.get(id=1)

# 安全获取单个对象（不存在则返回 None）
post = BlogPost.objects.filter(slug='my-first-post').first()

# 判断是否存在
if BlogPost.objects.filter(title='Hello World').exists():
    print("文章存在")
```

### 条件过滤

```python
# 查询已发布的文章
published_posts = BlogPost.objects.filter(is_published=True)

# 多条件 AND（默认）
posts = BlogPost.objects.filter(status='published', view_count__gte=100)

# 使用 __gt / __gte / __lt / __lte（大于/小于等）
popular_posts = BlogPost.objects.filter(view_count__gt=500)

# 日期范围查询
recent_posts = BlogPost.objects.filter(created_at__date=timezone.now().date())
last_week_posts = BlogPost.objects.filter(
    created_at__gte=timezone.now() - timezone.timedelta(days=7)
)

# 字段包含（模糊搜索，区分大小写）
posts_with_python = BlogPost.objects.filter(title__contains='Python')

# 忽略大小写包含
posts = BlogPost.objects.filter(title__icontains='django')

# 在某个列表中
top_authors = User.objects.filter(id__in=[1, 2, 3])
posts_by_top = BlogPost.objects.filter(author__in=top_authors)

# 排除条件
drafts = BlogPost.objects.exclude(status='published')  # 或用 filter(status__ne='published')
```

### 组合查询

Q 对象：实现 OR / NOT

```python
# OR 查询：状态为草稿 或 浏览量为0
from django.db.models import Q

inactive_posts = BlogPost.objects.filter(
    Q(status='draft') | Q(view_count=0)
)

# NOT 查询：非作者 ID=1 的文章
others_posts = BlogPost.objects.filter(~Q(author_id=1))

# 复杂组合：(已发布 且 评分≥4.0) 或 (作者是 admin)
admin_user = User.objects.get(username='admin')
posts = BlogPost.objects.filter(
    (Q(is_published=True) & Q(rating__gte=4.0)) |
    Q(author=admin_user)
)
```

### 排序与限制

```python
# 按评分降序 + 创建时间降序
posts = BlogPost.objects.order_by('-rating', '-created_at')

# 随机排序（慎用于大数据）
random_post = BlogPost.objects.order_by('?').first()

# 分页：取前10条
top_10 = BlogPost.objects.all()[:10]

# 跳过前5条，取接下来的5条（分页常用）
page_2 = BlogPost.objects.all()[5:10]
```

### 聚合统计

```python
# 统计总文章数
total = BlogPost.objects.count()

# 平均评分
avg_rating = BlogPost.objects.aggregate(Avg('rating'))  # 返回 {'rating__avg': 4.25}

# 每个作者的文章数量（annotate 为每行添加字段）
authors_with_counts = User.objects.annotate(post_count=Count('blogpost'))
for author in authors_with_counts:
    print(f"{author.username}: {author.post_count} 篇")

# 只获取高产作者（>5篇）
prolific_authors = User.objects.annotate(
    post_count=Count('blogpost')
).filter(post_count__gt=5)

# 使用 F 表达式：比较字段之间（如浏览量 > 10 * 评分）
from django.db.models import F
viral_posts = BlogPost.objects.filter(view_count__gt=F('rating') * 10)
```

### 关联查询

```python
# 正向查询：通过外键查作者信息（需提前获取 BlogPost 实例）
post = BlogPost.objects.get(id=1)
author_name = post.author.username  # 触发额外 SQL（N+1 问题）

# 优化：使用 select_related（一对一或外键）减少查询次数
post = BlogPost.objects.select_related('author').get(id=1)
# 此时 post.author 不会再查数据库

# 反向查询：查某用户的所有文章（User -> BlogPost）
user = User.objects.get(username='alice')
posts = user.blogpost_set.all()  # 默认反向关系名是 modelname_set

# 自定义反向关系名（若在 ForeignKey 中设置了 related_name='posts'，则用 user.posts.all()）

# 优化反向查询：prefetch_related（用于多对多或反向外键）
users_with_posts = User.objects.prefetch_related('blogpost_set').all()
for user in users_with_posts:
    for post in user.blogpost_set.all():  # 不会触发新查询
        print(post.title)
```

### 批量更新与删除

```python
# 批量更新：将所有草稿标记为未发布
BlogPost.objects.filter(status='draft').update(is_published=False)

# 批量删除：删除所有浏览量为0的草稿
BlogPost.objects.filter(status='draft', view_count=0).delete()

# 注意：update() 和 delete() 不会调用模型的 save() 或 delete() 方法，也不会触发信号！
```



## 事务管理





------

# 视图&路由

## 视图

Django支持两种视图函数定义：

1. 函数视图（Function-Based Views, FBV）
2. 类视图（Class-Based Views, CBV）

**函数视图：**

```python
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

def my_view(request: HttpRequest) -> HttpResponse:
    # request: HttpRequest 对象
    # 返回 HttpResponse 或其子类
    return HttpResponse("Hello from FBV!")

# 使用装饰器增强限制
@require_http_methods(["GET", "POST"])
def profile(request: HttpRequest) -> HttpResponse:
    return render(request, 'profile.html')
```

**类视图：**

使用 **Python 类** 封装视图逻辑，通过方法（如 `get()`, `post()`）区分 HTTP 方法。

```python
from django.http import HttpRequest, HttpResponse
from django.views import View

class MyView(View):
    def get(self, request: HttpRequest):
        return HttpResponse("Hello from CBV (GET)!")
    
    def post(self, request: HttpRequest):
        return HttpResponse("Hello from CBV (POST)!")
```

之后需要使用`.as_view()`方法转换成路由配置。

```python
# urls.py
path('myview/', MyView.as_view(), name='myview'),
```

**Django 内置的常见 CBV 类型如下：**

| 类别         | 典型类                                               | 用途                         |
| ------------ | ---------------------------------------------------- | ---------------------------- |
| **基础类**   | `View`                                               | 自定义任意逻辑               |
| **模板渲染** | `TemplateView`                                       | 直接渲染模板（无需写 `get`） |
| **重定向**   | `RedirectView`                                       | 返回 301/302 跳转            |
| **模型操作** | `ListView`, `DetailView`                             | 展示模型列表/详情            |
| **表单处理** | `FormView`, `CreateView`, `UpdateView`, `DeleteView` | CRUD 操作                    |

除了`View`，剩余的模板类都是用于前后端不分离的场景的。



## 路由

Django 支持 **多级路由**：

- **项目级路由**：`myproject/urls.py`（主入口）
- **应用级路由**：`myapp/urls.py`（模块化管理）

典型结构如下：

```txt
myproject/
├── myproject/
│   ├── settings.py
│   └── urls.py          ← 项目总路由
└── myapp/
    ├── views.py         ← 视图函数
    └── urls.py          ← 应用路由（可选但推荐）
```

路由配置过程如下：

```python
# ------ 应用级别路由汇总 ------
# myapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about, name='about'),
    path('books/<int:book_id>/', views.book_detail, name='book-detail'),
]

# ------ 项目总路由汇总 ------
# myproject/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),           # 包含 myapp 的路由，从myapp.urls中查找 urlpatterns 的变量
    path('blog/', include('blog.urls')),       # 另一个应用
]
```

上面的总路由汇总过程里使用的`include()`函数大致工作原理为：从指定的模块中查找`urlpatterns`的变量——不能使用其他的变量名，这是框架定死的。

`path()`函数用于配置URL和视图函数的映射，它的参数如下：

| 参数     | 类型         | 必填 | 说明                                     |
| -------- | ------------ | ---- | ---------------------------------------- |
| `route`  | `str`        | ✅ 是 | URL 路径模式（字符串）                   |
| `view`   | callable对象 | ✅ 是 | 视图函数或 `.as_view()` 返回的可调用对象 |
| `name`   | `str`        | ❌ 否 | URL 的唯一标识名，用于反向解析           |
| `kwargs` | `dict`       | ❌ 否 | 额外关键字参数，传递给视图               |

此外，还有一个`django.urls.re_path()`函数，可以采用正则表达式的方式进行路由配置。





------

# Admin管理后台

## 常用配置项

| 配置项                                  | 作用                       | 管理后台界面效果                                             |
| --------------------------------------- | -------------------------- | ------------------------------------------------------------ |
| `list_display`                          | 列表页显示哪些字段         | 表格列展示指定字段（支持方法）                               |
| `list_display_links`                    | 哪些字段可点击进入编辑页   | 对应列变成超链接                                             |
| `list_editable`                         | 哪些字段可在列表页直接编辑 | 显示为输入框/下拉框，保存后自动更新（不能与 `list_display_links` 冲突） |
| `list_filter`                           | 右侧筛选栏                 | 按字段值（如状态、日期、外键）提供过滤器                     |
| `search_fields`                         | 顶部搜索框                 | 支持按字段关键词全文搜索                                     |
| `ordering`                              | 列表默认排序               | 影响列表初始顺序（同 Model Meta.ordering，但优先级更高）     |
| `readonly_fields`                       | 编辑/详情页只读字段        | 显示为文本而非输入框                                         |
| `fields` / `fieldsets`                  | 控制编辑页字段布局         | `fields` 简单排列；`fieldsets` 分组+折叠+说明                |
| `filter_horizontal` / `filter_vertical` | 多对多字段选择器优化       | 将 `<select multiple>` 替换为左右穿梭框（更易用）            |
| `autocomplete_fields`                   | 外键/多对多字段自动补全    | 输入时异步搜索，适合大数据量关联                             |
| `date_hierarchy`                        | 顶部时间导航               | 按年/月层级钻取（需 DateField/DateTimeField）                |
| `show_full_result_count`                | 是否显示总记录数           | 默认 True，大数据时设为 False 提升性能                       |
| `actions`                               | 自定义批量操作             | 下拉菜单中添加自定义动作（如“批量发布”）                     |
| `save_as`                               | 编辑页显示“另存为”按钮     | 允许复制当前对象为新记录                                     |
| `save_on_top`                           | 顶部也显示保存按钮         | 编辑长表单时方便保存                                         |



## 综合示例

```python
# 基于 BlogPost 模型的完整 ModelAdmin 示例
# admin.py
from django.contrib import admin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """
    BlogPost 模型在 Django Admin 中的定制化配置
    """
    # ———————— 列表页配置 ————————
    # 在列表页显示哪些列（支持字段名、方法名、属性）
    list_display = (
        'title',
        'author',
        'status',
        'is_published',
        'view_count',
        'rating',
        'created_at',
        'publish_date',
    )

    # 点击哪一列可以进入编辑页面（默认第一列）
    list_display_links = ('title', 'author')

    # 哪些字段可以在列表页直接编辑（注意：不能和 list_display_links 重叠）
    list_editable = ('status', 'is_published', 'rating')

    # 右侧筛选栏：按状态、作者、是否发布、发布日期等筛选
    list_filter = (
        'status',
        'is_published',
        'author',
        'publish_date',
        'created_at',
    )

    # 顶部搜索框：支持按标题、内容、联系邮箱搜索（使用 icontains 模糊匹配）
    search_fields = ('title', 'content', 'contact_email')

    # 顶部时间导航：按创建年月钻取
    date_hierarchy = 'created_at'

    # 列表默认排序（覆盖 Model Meta.ordering）
    ordering = ('-created_at',)

    # 是否显示“共 XXX 条结果”（大数据量建议关闭）
    show_full_result_count = True

    # ———————— 编辑/详情页配置 ————————
    # 字段分组布局（比 fields 更灵活）
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'slug', 'author', 'status', 'is_published'),
            'description': "文章的核心元信息",
        }),
        ('内容与联系', {
            'fields': ('content', 'contact_email', 'source_url'),
            'classes': ('collapse',),  # 折叠该区域（点击展开）
        }),
        ('统计与评分', {
            'fields': ('view_count', 'rating', 'publish_date'),
            'classes': ('wide',),  # 宽布局（某些主题支持）
        }),
        ('时间信息（只读）', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # 设置只读字段（即使不在 fieldsets 中也要声明）
    readonly_fields = ('created_at', 'updated_at', 'slug')

    # 如果有 ManyToMany 字段（本例没有），可用以下方式优化：
    # filter_horizontal = ('tags',)   # 假设有 tags 字段

    # 外键自动补全（适合用户很多的情况）
    autocomplete_fields = ('author',)

    # 顶部也显示保存按钮（适合长表单）
    save_on_top = True

    # 允许“另存为新文章”
    save_as = True

    # ———————— 自定义动作（批量操作） ————————
    def make_published(self, request, queryset):
        """自定义动作：批量发布"""
        updated = queryset.update(is_published=True, status='published')
        self.message_user(request, f"成功发布 {updated} 篇文章。")
    make_published.short_description = "标记为已发布"

    def reset_views(self, request, queryset):
        """自定义动作：重置浏览量"""
        queryset.update(view_count=0)
        self.message_user(request, "浏览量已清零。")
    reset_views.short_description = "清零浏览量"

    # 注册自定义动作
    actions = ['make_published', 'reset_views']

    # ———————— 其他优化 ————————
    # 限制每页显示数量（默认100）
    list_per_page = 20

    # 自动补全搜索字段（配合 autocomplete_fields）
    # 注意：需要在 User Admin 中设置 search_fields 才能生效
```



**界面效果说明**：

- **列表页**：
  - 表格包含标题、作者、状态、是否发布、浏览量、评分、创建时间等列。
  - 标题和作者可点击进入编辑页。
  - 状态、是否发布、评分可直接在列表中修改并保存。
  - 右侧有“状态”、“作者”、“是否发布”等筛选器。
  - 顶部有搜索框和“2025年 > 11月”时间导航。
- **编辑页**：
  - 字段分为 4 个区域，其中“内容与联系”、“时间信息”默认折叠。
  - “创建时间”、“更新时间”、“slug”为只读。
  - 作者字段变为自动补全输入框（输入用户名即可搜索）。
  - 顶部和底部都有保存按钮。
  - 可点击“另存为”复制当前文章。
- **批量操作**：
  - 勾选多篇文章后，可从下拉菜单选择“标记为已发布”或“清零浏览量”。





------

# 用户认证&鉴权

参考文档：
+ 官方文档 [User authentication in Django](https://docs.djangoproject.com/en/4.2/topics/auth/)
+ 官方API文档 [`django.contrib.auth`](https://docs.djangoproject.com/en/4.2/ref/contrib/auth/)
+ [Django权限详解](https://pythondjango.cn/django/advanced/8-permissions/)

Django中的用户认证和鉴权系统联系的比较紧密，所以就一起介绍了。

这部分主要涉及到`django.contrib.auth.models`包中如下的3个对象，均是`django.db.models.Model`的子类：

+ `User`，记录了用户信息和权限信息，一些重要字段如下：
  + `id`：用户ID
  + `name`：用户名
  + `first_name`，`last_name`：用户姓名，可以为空
  + `email`：邮件地址
  + `password`：密码哈希值
  + `is_active`：是否为活跃用户
  + `is_staff`：是否为员工，也就是能否访问Admin信息
  + `is_superuser`：是否为超级管理员，可以对`User`表进行增删查改
  + `groups`：记录用户所属的组信息，和`Group`表相关的**多对多字段** —— 实际对应了一个专门的关联表
  + `user_permissions`：记录用户所具有的权限信息，和`Permission`表相关的**多对多字段** —— 实际对应了一个专门的关联表

+ `Group`，记录用户组信息（又被称为Role），主要字段如下：
  + `id`：组ID 
  + `name`：组名称
  + `permissions`：记录了组和权限的映射关系，**多对多字段** —— 也对应了一个关联表

+ `Permission`，记录权限信息，主要字段如下：
  + `id`：权限ID 
  + `name`：权限的描述，例如 'Can add log', 'Can change log', 'Can delete log'
  + `codename`：权限描述简写，例如 'add_log', 'change_log', 'delete_log'
  + `content_type`：权限对应的表模型的编号，是一个整数，它实际上是 `django_content_type` 表的主键
  

注意：
> Django提供的这套用户认证+鉴权的数据模型，功能跨度已经包含了下面的2个级别
> 1. 最基本的用户认证，比如通过用户名+密码来验证用户是否存在或登录正确
> 2. 基于角色的权限控制RBAC(Role-Based Access Control)

整体框架大致如下：
1. 在`settings.py`的`INSTALLED_APPS`里启用`django.contrib.auth  `模块之后
   + 后续每次对所有的App执行`makemigration`时，会扫描所有App下的数据模型，为每个数据模型生成对应的`Permission`记录，存放在**`auth_permission`**表中。
   + 对应于增删查改的4种权限，每个模型有4条记录，各个记录的`codename`为（假设模型为`Article`）：`add_article`,`delete_article`,`view_article`,`change_article`
   + 应用到具体的App上时，对应的权限名称就是：`{app_name}.{codename}`，比如blog应用的`Article`模型的权限名称就是`blog.add_article`,`blog.view_article`等

2. 后续增加用户组时，增加一个`Group`对象来记录该组的信息
   + 组的基本信息放在**`auth_group`**表中，里面只有`id`，`name`字段
   + `Group.permissions`是一个多对多字段，它单独存放在**`auth_group_permissions`**表中，存放该组和权限的多对多关系

3. 管理用户虽然是操作的`User`模型，但是底层有如下表：
   + 用户的基本信息管理存放在**`auth_user`**表中
   + `User.group`是一个多对多字段，对应的是**`auth_user_groups`**表，里面存放用户和组的映射关系
   + `User.permissions`也是多对多字段，对应的是**`auth_user_user_permissions`**表

上面的这 6 张表（`User`,`Group`,`Permission`和它们两两之间的关联表 3 个）就是`django.contrib.auth`模块实现 RBAC 用到的全部数据模型。
> 实际上一个 RBAC 系统，只需要 User, Group, Permission, User-Group, Group-Permission 这 5 张表就行，User-Permission 这张表不是必须的，Django 做了一些扩展而已。

实际使用中，`Permission`对应的权限模型是不需要我们来手动生成或者管理的，而且一般开发中，我们几乎不会直接操作`Permission`模型，主要的操作对象是用户和用户组，因此下面就不讨论`Permission`的使用。

## 用户和权限管理

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



## 认证&鉴权

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






--------
# Django RESTful 扩展

| 维度          | Django REST Framework (DRF)                 | Django Ninja                    |
|-------------|---------------------------------------------|---------------------------------|
| **设计哲学**    | 功能丰富、灵活、面向企业级应用                             | 简洁高效、受 FastAPI 启发、注重开发者体验       |
| **依赖**      | 基于 Django 内置组件（如 Form、ModelSerializer）      | 依赖 Pydantic（v1 或 v2）进行数据验证和序列化  |
| **类型提示支持**  | 有限（需额外配置或使用第三方库）                            | 原生支持 Python 类型注解（Type Hints）    |
| **自动文档**    | 通过 `drf-spectacular` 或 `coreapi` 实现 OpenAPI | 内置自动生成 OpenAPI 3 文档（类似 FastAPI） |
| **性能**      | 中等（因抽象层较多）                                  | 更高（更少中间层，Pydantic 验证快）          |
| **学习曲线**    | 较陡（概念多：ViewSet、Router、Serializer 等）         | 平缓（类似 FastAPI，函数式路由 + Pydantic） |
| **异步支持**    | 从 DRF 3.14+ 开始实验性支持 async views             | 原生支持 async/await（需 Django 3.1+） |
| **认证/权限系统** | 内置强大且灵活的权限、认证机制                             | 支持但相对简单，可集成 DRF 的认证后端           |
| **社区与生态**   | 极其庞大，插件丰富（如 JWT、OAuth、过滤器等）                 | 社区较小但活跃，生态正在成长                  |
| **适用场景**    | 复杂业务逻辑、需要深度定制的大型项目                          | 快速开发、微服务、对性能和类型安全有要求的项目         |

流行度对比：

| 指标                 | DRF                          | Django Ninja |
|--------------------|------------------------------|--------------|
| GitHub Stars       | ≈ 28k+                       | ≈ 8k+        |
| PyPI 下载量（月）        | 数百万                          | 数十万（快速增长中）   |
| Stack Overflow 问题数 | >50k                         | <2k          |
| 官方文档完善度            | 非常完善                         | 良好，简洁清晰      |
| 企业采用率              | 高（如 Mozilla、Instagram 等早期用户） | 中小公司或新项目较多   |






--------
## Django REST Framework(DRF)

### 安装

```shell
# pip
pip install djangorestframework
# conda
conda install -c conda-forge djangorestframework

# JWT认证的扩展
pip install djangorestframework_simplejwt
# 不能使用 conda 安装，因为 conda-forge 里的版本只更新到 4.x，不适配 Django 4.2，需要使用 pip 安装最新的 5.x 版本
# conda install -c conda-forge djangorestframework_simplejwt
```





--------
## Django Ninja

Django Ninjia 相比DRF有如下特点：
1. 使用了Pydantic进行校验+序列化，
2. 使用类型提示来进行变量标注
3. 支持OpenAPI(也就是Swagger)，提供了SwaggerUI的API Docs界面，并供调试
4. URL申明通过装饰器的方式，**和视图函数定义放在一起**，而不是在单独的url文件中关联——这一点和Flask或者FastAPI很接近了

> 个人感觉上手要比 DRF 简单，提供了类似于FastAPI的使用体验，实际上，这个扩展的作者就是受FastAPI启发的。