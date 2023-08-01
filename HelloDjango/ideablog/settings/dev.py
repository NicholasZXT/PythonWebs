from .base import *     # NOQA


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'hello_django',
        'USER': 'root',
        'PASSWORD': 'mysql2022',
        'HOST': 'localhost',
        'PORT': 3306,
        # 'CONN_MAX_AGE': 5*60,
        # 'OPTIONS': {'charset': 'utf8bm4'}
        'MYSQL': {
            'driver': 'pymysql',  # 使用pymysql作为数据库客户端
            'charset': 'utf8mb4',
        },
    }
}