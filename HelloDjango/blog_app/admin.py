from django.contrib import admin
from .models import Post, Category, Tag

# Register your models here.
# 官方文档 https://docs.djangoproject.com/en/4.2/ref/contrib/admin/
# 定义 blog_app 中有哪些 Model 需要加入到 Django Admin 管理后台中。
# django.contrib.admin.ModelAdmin 是Django Admin管理后台中用于封装 待管理数据模型 的基类，
# 如果需要自定义在 Admin界面 如何展示和修改 被管理ORM模型类的字段，需要继承此类进行定制，并随 被管理ORM模型 一同注册到 Admin 中。

# 有如下 3 种注册方式：

# 1. 如果不需要在admin界面自定义要展示的ORM数据模型的内容，可以直接使用如下的方式
# admin.site.register(Category)

# 2. 使用装饰器语法糖来注册 被管理的模型类Category，同时关联 对应的Admin类 CategoryAdmin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # CategoryAdmin 继承于 admin.ModelAdmin，可以用来定义在 Admin 页面上如何展示 Category 模型相关的信息
    # 通过如下的类属性，在 admin管理界面定义数据模型的显示或者操作

    # 定义下拉框可以进行的操作，需要传入一些函数
    # actions = []

    # 指定admin界面上要管理的字段，这些字段会在表单中显示，并提供管理功能
    fields = ('owner', 'name', 'status', 'is_nav')

    # 需要排除的一些字段，被排除的这些字段，admin管理界面的表单中不会提供对应的管理功能
    # exclude = []

    # 指定admin界面 change list 里要展示的字段
    list_display = ('name', 'status', 'is_nav', 'created_time')


# 3. 使用 admin.site.register手动建立 被管理ORM模型类 和 对应Admin类 之间的联系，并注册到 Admin 的管理内容中
class TagAdmin(admin.ModelAdmin):
    fields = ('name', 'status')
    list_display = ('name', 'status')

admin.site.register(Tag, TagAdmin)
