from functools import wraps
from flask_classful import FlaskView, route


def dec(fun):
    """一个无参装饰器"""
    @wraps(fun)
    def wrapper(*args, **kwargs):
        print(f"-->[wrapper] custom decorator called without param for method : {fun.__name__} ...")
        return fun(*args, **kwargs)
    return wrapper

def dec_param(param=None):
    """一个带参装饰器"""
    def dec_inner(fun):
        @wraps(fun)
        def wrapper(*args, **kwargs):
            print(f"-->[wrapper] custom decorator called with param '{param}' for method: {fun.__name__} ...")
            return fun(*args, **kwargs)
        return wrapper
    return dec_inner


# 这里继承 FlaskView 之后，在 main.py 里通过 ClassBaseViews.register(app) 注册里面定义的视图函数
class ClassBasedViews(FlaskView):
    # route_prefix 和 route_base 的作用一样，但是如果同时设定，那么 route_prefix 在 route_base 之前
    route_prefix = '/prefix'
    route_base = '/base'
    # 需要排除的方法，这些方法不会注册为视图函数
    excluded_methods = ['exclude_fun']
    # 统一设置装饰器，应用于每个视图函数上
    decorators = [dec, dec_param(param='hello')]

    # 手动设置视图函数
    @route('/info', methods=['GET'])
    def info(self):
        result = "Flask-classful: info method is called ..."
        print(result)
        return result

    # 默认下，方法会被注册成一个 'GET {route_base}/auto_info' 端点对应的视图函数
    def auto_info(self):
        result = "Flask-classful: auto_info method is called ..."
        print(result)
        return result

    # 特殊名字的方法会被注册成对应的视图，比如 get, post, index, delete 等
    def get(self):
        result = "Flask-classful: special get method is called ..."
        print(result)
        return result

    # 需要排除的方法放在 类的 excluded_methods 属性里
    def exclude_fun(self):
        return "exclude"

    # ------------ 请求的hook方法 ---------------
    # 执行顺序为： before_request  --> before_{view_name} --> view function --> after_{view_name} --> after_request
    # 对所有视图方法都生效
    def before_request(self, name, **kwargs):
        # name 是待执行的视图方法名称，kwargs 是请求的其他参数
        print(f"==>[all_hook] before_request is called for view function '{name}' with kwargs: {kwargs} ...")
        # 通常不需要返回值（也就是返回None）
        # 如果返回值不为 None，那么此处的返回值就会代替后续视图函数返回值，导致后续的视图函数不会执行
        # return "before_request result"

    def after_request(self, name, response):
        # name 是已执行的视图方法名称，response 是对应视图函数的返回值
        print(f"==>[all_hook] after_request is called for view function '{name}' with response: {response} ...")
        # 必须要有返回值——通常就是视图函数的返回值
        return response

    # 对指定视图方法生效，此时方法名称必须为 before_{view_name} / after_{view_name}
    def before_info(self, **kwargs):
        # 此时就没有 name 参数了（因为这里肯定是 info 视图函数的hook），kwargs 仍然是请求的其他参数
        print(f"==>[info_hook] before_info is called with kwargs: {kwargs} ...")
        # 同样，一般没有返回值（返回None），否则非None返回值会导致后续视图函数不执行
        # return "before_info result"

    def after_info(self, response):
        # 此时也没有 name 参数了，response 仍然是视图函数的返回值
        print(f"==>[info_hook] after_info is called with response: {response} ...")
        # 必须要有返回值——通常是传入的response
        return response

