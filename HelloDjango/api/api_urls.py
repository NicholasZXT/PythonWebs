from django.urls import path, re_path
from .views import get_student, list_student, create_student, TeacherApiView, TeacherGenericView, \
    TeacherCompositeView, TeacherViewSet
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.routers import DefaultRouter

# ViewSet 需要使用 Router 来集成
router = DefaultRouter()
router.register(r'teacher/viewset', viewset=TeacherViewSet)

urlpatterns = [
    path('get_student/<int:sid>', get_student),
    path('list_student', list_student),
    path('create_student', create_student),
    # ------- Class-based 视图 ---------
    # 由于这里设置了 tid 参数，所以 TeacherApiView 里的所有方法，包括 post，都必须要接受一个 tid 参数，即使用不到
    path('teacher/apiviews/<int:tid>', TeacherApiView.as_view()),
    # 其他class-based view
    path('teacher/genericviews/<int:tid>', TeacherGenericView.as_view()),
    path('teacher/compositeviews', TeacherCompositeView.as_view()),
]

# 默认下，DRF 框架的 Response 对象会对接口返回的数据使用默认的HTML页面进行渲染，稍微封装一下，容易查看数据
# 在视图函数里加上一个 format=None 参数，然后使用下面的方式进行后缀匹配，可以在 URL 的末尾使用 .json 的方式指定返回原始的JSON数据，而不是渲染的页面
urlpatterns = format_suffix_patterns(urlpatterns)
# print(urlpatterns)
# 集成 ViewSet 里的视图函数
urlpatterns += router.urls
