import sys
import os
from urllib import parse

basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # 用于生成token的KEY
    SECRET_KEY = 'flask-insecure-nv6-(i1-659xonvcxe&luz90!jsp0ag!y7lt0_8-01al#iilw2'
    # 认证用户
    AUTHORIZED_USER = {'yourself': 'f**k'}
    # 过期时间，单位s
    TOKEN_EXPIRATION = 60 * 5

class DevelopmentConfig(BaseConfig):
    mysql_conf = {
        'user': '',
        'passwd': parse.quote_plus(''),
        'host': 'localhost',
        'port': 3306,
        'db': ''
    }
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}".format(**mysql_conf)

config = {
    'dev': DevelopmentConfig
}
