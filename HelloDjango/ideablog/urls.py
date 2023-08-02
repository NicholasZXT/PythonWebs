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
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

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
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.api_urls'))  # 使用 include 引入 api 应用下的路由映射
]
