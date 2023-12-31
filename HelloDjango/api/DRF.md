# Django REST Framework (DRF)

## 安装

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

> 除了DRF框架用于开发 REST 接口，还有一个 Django Ninjia，有如下特点：
> 1. 使用了Pydantic进行校验+序列化，
> 2. 使用类型提示来进行变量标注
> 3. 支持OpenAPI(也就是Swagger)，提供了SwaggerUI的API Docs界面，并供调试
> 4. URL申明通过装饰器的方式，**和视图函数定义放在一起**，而不是在单独的url文件中关联——这一点和Flask或者FastAPI很接近了
> 感觉上手要比 DRF 简单，提供了类似于FastAPI的使用体验，实际上，这个扩展的作者就是受FastAPI启发的。