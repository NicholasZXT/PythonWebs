from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Category(models.Model):

    # 表的元数据信息通过一个内部类 Meta 来设置，这些元数据信息也是可选的
    class Meta:
        managed = True   # 是否交由 ORM 框架管理，默认为True
        # db_tablespace = 'dbbase'   # 数据库
        db_table = 'blog_category'           # 设置表名称，默认下Django会以全小写的 {app_name}_{model_class_name} 形式创建表
        db_table_comment = '博客文章类别'      # 设置表的注释, 4.2版本开始才有这个功能
        verbose_name = '类别'                 # 此Model的文本表示，用于在 Django Admin 界面显示等
        verbose_name_plural = verbose_name   # 复数形式，默认下会在 verbose_name 后面加上字符串 s 表示复数（比如在Admin界面显示时）
        ordering = ['name', '-status']       # 指定数据记录的排序字段，默认ASC，- 表示 DESC
        # 定义索引字段
        indexes = [models.Index(fields=["name"])]

    # 设置一些常量，这些变量和Django框架无关
    STATUS_NORMAL = 1
    STATUS_DELETE = 0
    STATUS_ITEM = {
        (STATUS_NORMAL, '正常'),
        (STATUS_DELETE, '删除'),
    }
    # 定义字段
    # 默认下，如果用户没有定义主键，Django会使用类似下面的语句创建一个自增主键
    # id = models.BigAutoField(primary_key=True)
    # db_comment 是字段的注释，从 4.2 版本开始才有
    name = models.CharField(max_length=50, verbose_name='名称', db_comment="名称")
    status = models.PositiveIntegerField(default=STATUS_NORMAL, choices=STATUS_ITEM, verbose_name='状态')
    is_nav = models.BooleanField(default=False, verbose_name='是否为导航')
    owner = models.ForeignKey(User, verbose_name="作者", on_delete=models.DO_NOTHING)
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')


class Tag(models.Model):

    class Meta:
        db_table = 'blog_tag'
        db_table_comment = '博客标签'
        verbose_name = '标签'
        verbose_name_plural = verbose_name
        ordering = ['-id']

    STATUS_NORMAL = 1
    STATUS_DELETE = 0
    STATUS_ITEMS = (
        (STATUS_NORMAL, '正常'),
        (STATUS_DELETE, '删除'),
    )

    name = models.CharField(max_length=10, verbose_name="名称")
    status = models.PositiveIntegerField(default=STATUS_NORMAL, choices=STATUS_ITEMS, verbose_name="状态")
    owner = models.ForeignKey(User, verbose_name="作者", on_delete=models.DO_NOTHING)
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return self.name


class Post(models.Model):

    class Meta:
        db_table = 'blog_post'
        db_table_comment = '博客文章'
        verbose_name = verbose_name_plural = "文章"
        # ordering = ['-id']

    STATUS_NORMAL = 1
    STATUS_DELETE = 0
    STATUS_DRAFT = 2
    STATUS_ITEMS = (
        (STATUS_NORMAL, '正常'),
        (STATUS_DELETE, '删除'),
        (STATUS_DRAFT, '草稿'),
    )

    title = models.CharField(max_length=255, verbose_name="标题")
    desc = models.CharField(max_length=1024, blank=True, verbose_name="摘要")
    content = models.TextField(verbose_name="正文", help_text="正文必须为MarkDown格式")
    content_html = models.TextField(verbose_name="正文html代码", blank=True, editable=False)
    status = models.PositiveIntegerField(default=STATUS_NORMAL, choices=STATUS_ITEMS, verbose_name="状态")
    is_md = models.BooleanField(default=False, verbose_name="markdown语法")
    tag = models.ManyToManyField(Tag, verbose_name="标签")
    category = models.ForeignKey(Category, verbose_name="分类", on_delete=models.DO_NOTHING)
    owner = models.ForeignKey(User, verbose_name="作者", on_delete=models.DO_NOTHING)
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    pv = models.PositiveIntegerField(default=1)
    uv = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.title
