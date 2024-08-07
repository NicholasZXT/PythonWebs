import sys
from time import sleep
import logging
from logging.handlers import TimedRotatingFileHandler
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

LOG_FORMAT = "%(levelname)s, %(asctime)s, %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志配置
def getLogger(log_file: str = 'flask.log', name: str = None, write_file: bool = False):
    """ 滚动日志器 """
    name = name if name else __name__
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    # 控制台输出
    console_handler = logging.StreamHandler()
    # console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    if write_file:
        # 轮换文件输出
        # 每隔 interval 轮换一次， when 为单位，M 表示分钟 —— 每分钟轮换一次日志文件
        rotate_handler = TimedRotatingFileHandler(filename=log_file, when='M', interval=1, encoding='utf-8')
        # 每天轮换一次日志文件
        # rotate_handler = TimedRotatingFileHandler(filename=log_file, when='D', interval=1, encoding='utf-8')
        # 每周一轮换一次文件
        # rotate_handler = TimedRotatingFileHandler(filename=log_file, when='W0', encoding='utf-8')
        rotate_handler.setFormatter(formatter)
        logger.addHandler(rotate_handler)
    return logger


if __name__ == '__main__':
    logger = getLogger('test.log')
    cnt = 1
    while cnt <= 50:
        logger.info(f"info log with count: {cnt}")
        sleep(2)
        cnt += 1
