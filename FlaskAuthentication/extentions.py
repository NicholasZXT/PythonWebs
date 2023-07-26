# 所有扩展的依赖和对象的初始化都放到这里，以便进行模块拆分
import os
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()