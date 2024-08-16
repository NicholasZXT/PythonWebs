from flask import Blueprint, request, jsonify, Request
from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.exceptions import HTTPException, InternalServerError
import json
from marshmallow import Schema, ValidationError
from webargs.flaskparser import parser, use_args, use_kwargs
from webargs import fields, validate

webargs_bp = Blueprint('webargs', __name__, url_prefix='/webargs')

# 使用 webargs，麻烦的地方其实是在校验失败后，返回合适的异常信息，因为默认下抛出的是 mashmallow 的 ValidationError,
# 这个异常被 Flask 捕获后，对外统一抛出的是 werkzeug.exceptions 下的 InternalServerError，看不到具体的校验错误信息
# 因此这里需要继承 werkzeug.exceptions.HTTPException 来自定义一个校验错误的 Exception
class ValidationFailed(HTTPException):
    """
    HTTPException 是 werkzeug.exceptions 里所有异常的基类，因此也是Flask里大部分网络相关异常的基类.
    自定义异常时，参照 HTTPException 的源码，通常需要重写下面3个方法：
    + get_headers
    + get_description
    + get_body，
    get_response 方法一般不需要重写，使用 HTTPException 基类提供的就行，它会调用上面的3个方法组成响应。
    """
    code: int = 400
    description: str = "Validation Failed !"
    error_msg: str | dict = None

    def __init__(self, description=None, response=None, error_msg=None) -> None:
        """
        description 和 response 是父类需要的参数；
        error_msg 是自定义的参数.
        """
        super().__init__(description=description, response=response)
        if description is not None:
            self.description = description
        self.response = response
        self.error_msg = error_msg

    def get_headers(self, environ=None, scope=None):
        """Get a list of headers."""
        return [('Content-Type', 'application/json')]

    def get_description(self, environ=None, scope=None) -> str:
        """Get the description."""
        # 实际上可以直接重写 get_body 方法，不需要借助此方法，不过这里是为了覆盖掉父类的方法
        return self.description

    def get_body(self, environ=None, scope=None) -> str:
        """这里返回 JSON格式 数据，而不是默认的 HTML格式"""
        body = dict(
            code=self.code,
            desc=self.description,
            error_msg=self.error_msg
        )
        body_str = json.dumps(body)
        return body_str


# webargs 底层使用 marshmallow 进行校验，所以 schema 的定义参考 marshmallow 即可
user_schema = {
    "username": fields.Str(required=True),
    "gender": fields.Str(required=True, validate=validate.OneOf(['male', 'female'])),
    "age": fields.Int(required=False, validate=validate.Range(min=1, max=120)),
    "email": fields.Email(required=False),
    "password": fields.Str(required=True, validate=validate.Length(min=4, max=16)),
}


# 第一种使用方式，使用 parser 解析请求
# 注册parser的自定义错误处理器
@parser.error_handler
def handle_error(error: ValidationError, req: Request, schema, *, error_status_code, error_headers):
    """
    此错误处理函数必须接受的参数如下：
    :param error: 具体的错误
    :param req: 请求对象
    :param schema: 使用的 schema 对象
    :param error_status_code: 状态码
    :param error_headers: 请求头
    :return:
    """
    # print(error.data)
    # print(error.valid_data)
    # print(error.messages)
    print(f"parser.error_handler.hook -> error: {error}")
    # msg = error.messages.get('json', {})
    msg = error.messages
    # 上面拿到的 msg 是一个dict
    # msg = json.dumps(msg)
    raise ValidationFailed(error_msg=msg)

@webargs_bp.route("/register/v1", methods=["POST"])
def register_v1():
    args = parser.parse(argmap=user_schema, req=request)
    print(f"register-v1 -> args: {args}")
    return jsonify(args)


# 第2种使用方式，使用 user_args 装饰器
@webargs_bp.route("/register/v2", methods=["POST"])
@use_args(user_schema, location="json")  # location 指定参数从哪里解析
def register_v2(args):  # 此时视图函数必须要接受一个arg参数，存放解析的内容，可能是dict，或者是其他的形式
    print(f"register-v2 -> args: {args}")
    return jsonify(args)


# 第3种方式，使用 use_kwargs 装饰器
@webargs_bp.route("/register/v3", methods=["POST"])
@use_kwargs(user_schema)
def register_v3(username, gender, age, email, password):  # 此时视图函数必须要接受关键词参数，存放解析的内容
    args = {'username': username, 'gender': gender, 'age': age, 'email': email, 'password': password}
    print(f"register-v3 -> args: {args}")
    return jsonify(args)

# 上面装饰器的两种方式，需要通过添加异常处理器来捕获校验异常
@webargs_bp.errorhandler(ValidationError)   # 只处理 ValidationError
def handle_validation_err(error: ValidationError):
    # print(error.data)
    # print(error.valid_data)
    # print(error.messages)
    print(f"parser.error_handler.hook -> error: {error}")
    # msg = error.messages.get('json', {})
    msg = error.messages
    # 上面拿到的 msg 是一个dict
    msg = json.dumps(msg)
    raise ValidationFailed(error_msg=msg)
