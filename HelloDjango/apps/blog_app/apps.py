from django.apps import AppConfig

# 这里用于定义每个Application自己的配置项
# 对于每个App来说，这个文件不是必须的，如果没有此文件，就会使用默认的基类AppConfig作为配置
class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog_app'
