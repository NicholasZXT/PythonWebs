import sys
import os
from urllib import parse
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # 用于生成token的KEY
    SECRET_KEY = 'flask-insecure-nv6-(i1-659xonvcxe&luz90!jsp0ag!y7lt0_8-01al#iilw2'
    # JWT使用的秘钥
    JWT_SECRET_KEY = 'flask-insecure-nv6-(i1-659xonvcxe&luz90!jsp0ag!y7lt0_8-01al#iilw2jwt'
    # JWT的token刷新时间设置
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    # JWT设置请求中可以存放JWT信息的位置
    JWT_TOKEN_LOCATION = ["headers"]
    # 认证用户，附带了用户的角色信息
    AUTHORIZED_USERS = {
        'admin': {'passwd': 'admin', 'uid': 1, 'username': 'admin', 'roles': ['admin']},
        'yourself': {'passwd': 'people', 'uid': 2, 'username': 'yourself', 'roles': ['others']},
    }
    # 过期时间，单位s
    TOKEN_EXPIRATION = 60 * 20

class DevelopmentConfig(BaseConfig):
    mysql_conf = {
        'user': 'root',
        'passwd': parse.quote_plus('mysql2022'),
        'host': 'localhost',
        'port': 3306,
        'db': 'hello_flask'
    }
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}".format(**mysql_conf)


config = {
    'dev': DevelopmentConfig
}
