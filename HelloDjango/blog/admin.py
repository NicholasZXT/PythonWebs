from django.contrib import admin
from .models import Post, Category, Tag

# Register your models here.

# 使用装饰器快速注册
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'is_nav', 'created_time')
    # 指定admin界面上要展示的字段
    fields = ('owner', 'name', 'status', 'is_nav')

# 另一种注册方式
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')
    fields = ('name', 'status')


admin.site.register(Tag, TagAdmin)