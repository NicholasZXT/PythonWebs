import sys
import os
from urllib import parse

basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfig:
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True

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
