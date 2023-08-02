from django.urls import path
from .views import get_student, list_student
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path('get_student/<int:sid>', get_student),
    path('list_student', list_student)
]

# 默认下，DRF 框架的 Response 对象会对接口返回的数据使用默认的HTML页面进行渲染，稍微封装一下，容易查看数据
# 在视图函数里加上一个 format=None 参数，然后使用下面的方式进行后缀匹配，可以在 URL 的末尾使用 .json 的方式指定返回原始的JSON数据，而不是渲染的页面
urlpatterns = format_suffix_patterns(urlpatterns)
# print(urlpatterns)