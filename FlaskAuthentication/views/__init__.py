from .rest_auth import *
from .login_auth import *
# 这里还不能使用下面只导入蓝图的方式，否则 main.py 里 的 db.create_all() 就不会创建表，原因未知 #TODO
# from .rest_auth import auth_bp
# from .login_auth import login_bp
