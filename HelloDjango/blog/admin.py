from django.contrib import admin
from .models import Post, Category, Tag

# Register your models here.
# admin.ModelAdmin 是Django admin管理后台中用于封装待管理的数据模型的基类，所有需要被 admin 管理的ORM模型，都需要继承此类，并进行注册。
# 官方文档 https://docs.djangoproject.com/en/4.2/ref/contrib/admin/

# 有如下 3 种注册方式：

# 1. 如果不需要在admin界面自定义要展示的数据模型的内容，可以直接使用如下的方式
# admin.site.register(Category)

# 2. 使用装饰器快速注册，这种方式可以自定义页面上需要展示的内容
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # 通过如下的类属性，在 admin管理界面定义数据模型的显示或者操作
    # 定义下拉框可以进行的操作，需要传入一些函数
    # actions = []
    # 指定admin界面上要管理的字段，这些字段会在表单中显示，并提供管理功能
    fields = ('owner', 'name', 'status', 'is_nav')
    # 需要排除的一些字段，被排除的这些字段，admin管理界面的表单中不会提供对应的管理功能
    # exclude = []
    # 指定admin界面 change list 里要展示的字段
    list_display = ('name', 'status', 'is_nav', 'created_time')


# 3. 另一种注册方式
class TagAdmin(admin.ModelAdmin):
    fields = ('name', 'status')
    list_display = ('name', 'status')

admin.site.register(Tag, TagAdmin)