"""blog URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog_app/', include('blog_app.urls'))

对于 Django 1.1.x 版本，使用的是如下函数
from django.conf.urls import url
urlpatterns = [
    url(r'^admin/$', admin.site.urls),
    url(r'^index/$', views.index), # 普通路径
    url(r'^articles/([0-9]{4})/$', views.articles), # 正则路径
]

对于 Django 2.2.x 之后的版本
from django.urls import path, re_path # 用re_path 需要引入
urlpatterns = [
    path('admin/', admin.site.urls),
    path('index/', views.index), # 普通路径
    re_path(r'^articles/([0-9]{4})/$', views.articles), # 正则路径
]

path函数签名如下(https://docs.djangoproject.com/zh-hans/4.1/ref/urls/)：
path(route, view, kwargs=None, name=None)
  route: 字符串，用于指定 URL 的模式，其中可以使用 <username> 这种方式来捕获URL中对应位置的内容，更近一步，可以使用 <str:username> 来进行类型转换
  view: 是一个 视图函数 或 as_view() 的结果，用于基于类的视图。它也可以是一个 django.urls.include()，用于包含各个app里定义的 urls.py 文件
  kwargs: 允许你向视图函数或方法传递附加参数
  name: 路由别名，用于反向解析路由
"""
import json
from django.contrib import admin
from django.urls import path, include
from django.core.handlers.wsgi import WSGIRequest
from django.http.response import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_GET

# -------------- 这里展示了一些简单请求 ----------------------
@require_http_methods(request_method_list=['GET'])  # 这个视图装饰器是可选的，这里使用它来限制视图函数可以接受的请求类型
def hello(request: WSGIRequest):
    # 视图函数必须要接受一个 request 参数，它是 WSGIRequest 对象
    print('request: ', request)
    print('request.__class__: ', type(request))
    # 视图函数的返回值必须要用 HttpResponse(及其子类) 封装起来，或者调用 render() 方法返回渲染的HTML
    # HttpResponse的默认类型是 content_type='text/html'
    return HttpResponse(content="<h1>Hello Django!</h1>", content_type='text/html')

# 返回JSON数据
@require_GET
def hello_json(request: WSGIRequest):
    json_data = {'k1': 'v1', 'k2': 'v2'}
    # 使用 HttpResponse 封装时，需要手动 dumps
    json_data = json.dumps(json_data)
    return HttpResponse(content=json_data, content_type='application/json')

@require_GET
def hello_json_v2(request: WSGIRequest):
    json_data = {'k1': 'v1', 'k2': 'v2'}
    # 使用 JsonResponse 时，则不需要手动 dumps，也不需要手动设置 content_type，但是参数名为 data
    return JsonResponse(data=json_data)


# ------------ 所有请求的URL和视图函数的映射关系 ---------------
urlpatterns = [
    path('', hello),   # 根路径不需要指定 /
    path('admin/', admin.site.urls),   # Django Admin 管理界面的URL路由
    path('hello_json/', hello_json),
    path('hello_json_v2/', hello_json_v2),
    path('api/', include('api.api_urls')),  # 使用 include 引入 api 应用下的路由映射
]
