import os
import logging
from logging.handlers import TimedRotatingFileHandler


LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"  # 默认格式
LOG_FORMAT = "[%(levelname)s][%(asctime)s] %(message)s"
# LOG_FORMAT = "[%(levelname)s][%(asctime)s][%(processName)s][%(funcName)s] %(message)s"


def getLogger(name: str = None, debug: bool = False, write_file: bool = False, log_file: str = None) -> logging.Logger:
    """ 滚动日志器 """
    name = name if name else __name__
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, 'logs')):
        os.makedirs(os.path.join(cwd, 'logs'), exist_ok=True)
    logger = logging.getLogger(name)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    # 控制台输出
    # console_handler = logging.StreamHandler()
    # console_handler = logging.StreamHandler(stream=sys.stdout)
    # console_handler.setFormatter(formatter)
    # logger.addHandler(console_handler)
    if write_file:
        log_file = log_file if log_file else name + '.log'
        log_file_path = os.path.join(cwd, 'logs', log_file)
        # 轮换文件输出
        # 每天轮换一次日志文件
        # rotate_handler = TimedRotatingFileHandler(filename=log_file_path, when='D', interval=1, encoding='utf-8')
        # 每周一轮换一次文件
        rotate_handler = TimedRotatingFileHandler(filename=log_file_path, when='W6', encoding='utf-8')
        rotate_handler.setFormatter(formatter)
        logger.addHandler(rotate_handler)
    return logger