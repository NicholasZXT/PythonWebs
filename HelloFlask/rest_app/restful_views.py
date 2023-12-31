from flask import Blueprint, request
from flask_restful import Api, Resource, reqparse, inputs, fields, marshal_with
from datetime import datetime
from flask.views import View, MethodView


restful_bp = Blueprint('rest', __name__, url_prefix='/rest')
# 这里当然也可以使用 Flask 对象
api = Api(restful_bp)

# Flask-restful 提供了一个 reqparse 类，用于实现参数 解析 和 验证 的功能 —— 主要是参数验证功能，参数解析的话Flask的request对象就可以完成
# **********************************************************************************************************************
# 看了下源码，reqparse.RequestParser 也可以用单独使用，并不是和 flask_restful 里的 Api、Resource 耦合的，它唯一耦合的地方就是
# 出错时，调用 flask_restful.abort() 方法返回错误信息.
# **********************************************************************************************************************

# reqparse 的用法和 argparse 类似：
# 使用下面的 add_argument() 方法添加需要解析验证的参数：
#  1. location: 指定参数从哪个地方解析，默认会从 Request.values 和 Request.json 里解析.
#     args 表示从 URL 路径解析； json 表示从 POST/PUT 请求体 json 解析； form 表示从 POST 表单 解析； headers 表示从请求头解析
#     可以用 列表/元组 的形式传入多个值。
#  2. required: 指定参数是否为必须，默认 False
#  3. default: 默认值
#  4. choices: 选项参数，限制取值
#  5. action: 参数行为, append 表示可以接受多个值
#  6. help: 帮助信息，用于参数验证错误时显示
parser = reqparse.RequestParser()
parser.add_argument('arg', type=str, required=True, location='args', help='arg')
parser.add_argument('arg_default', type=str, default='default_value', location='args', help='arg_default')
parser.add_argument('array', action='append', location='args', help='array')

# 使用如下方法解析参数，返回值是 dict —— 注意，必须要在视图函数中进行解析，因为它需要一个具体的 Request 上下文环境
# 使用 strict=True 参数时，如果传入了未定义的参数，则会返回错误
# args = parser.parse_args()

# 可以使用 .copy() 方法复制一份 parser，继承已有的参数，然后使用 .replace_argument() 或者 .remove_argument() 方法修改已有参数
# parser_copy = parser.copy()
# parser_copy.remove_argument('arg')
# parser_copy.replace_argument('array', type=str)
# args_copy = parser_copy.parse_args()

# ****************************************************************************************************
# 这里有个坑需要特别注意，对于 GET, DELETE 等没有请求体的方法，RequestParser.add_argument() 里的 location 只能是 args，
# 不能有需要从 json 里解析的参数，否则会导致一直无法解析请求
# ****************************************************************************************************

# Flask-restful 还提供了一个 inputs ，封装了一些常用的类型校验，可以作为 type= 的参数
# 下面的参数都来自 POST 请求体，做一份copy，和 GET 请求的 parser 区分开
parser_body = parser.copy()
parser_body.add_argument('boolean', type=inputs.boolean, location='json', help='boolean should in {true, false}')
parser_body.add_argument('date', type=inputs.date, location='json', help='date should in yyyy-mm-dd')
parser_body.add_argument('pos_int', type=inputs.positive, location='json', help='pos_int should > 0')
parser_body.add_argument('range_int', type=inputs.int_range(0, 20), location='json', help='range_int should in [0, 20]')

# 常用的分页参数
parser.add_argument('size', type=inputs.int_range(5, 20), default=20, location='args', help='page size should in [5, 20]')
parser.add_argument('index', type=inputs.positive, default=1, location='args', help='page index should > 0')

# Resource 类实际上是对 MethodView 类的封装
class ParserTest(Resource):
    def get(self):
        # RequestParser 对象必须在视图函数中解析验证
        # GET 请求使用的 RequestParser 里，不能有 location='json' 的参数，否则会报错，所以这里不能使用 parser_body 这个 parser
        args = parser.parse_args()
        result = {
            'arg': args.arg,  # 这个参数必须要有，否则会返回 400，提示缺少该请求参数
            'arg_default': args.arg_default,  # 有默认值的参数
            # 没有解析到的参数，默认为 None，不会报错，最后会被转成 JSON 的 null
            'array': args.array,
            'size': args.size,
            'index': args.index,
        }
        return result, 200

    def post(self):
        # POST 请求使用的是 parser_body 这个 parser
        args = parser_body.parse_args()
        # 没有传入的haul，参数值是 None
        print('args.pos_int: ', args.pos_int)
        # date 如果有，是 datetime.datetime 类型
        print('args.date.__class__: ', type(args.date))
        result = {
            'arg': args.arg,  # 这个参数必须要有，否则会返回 400，提示缺少该请求参数
            'arg_default': args.arg_default,  # 有默认值的参数
            # 下面的参数，如果没有解析到，默认都为 None，不会报错，最后会被转成 JSON 的 null
            'array': args.array,

            # 以下为 post 请求体参数
            'boolean': args.boolean,
            # datetime.datetime 类型默认下不能被序列化
            'date': args.date.strftime('%Y-%m-%d') if args.date else None,
            'pos_int': args.pos_int,
            'range_int': args.range_int
        }
        return result, 200


# ----------------------------------------------------------------------------------------------------------------------
# 模拟数据
PERSON = {
    'ming': {'name': 'ming', 'age': 20, 'birthday': datetime.strptime('1990-01-01', '%Y-%m-%d'),
             'address': {'province': 'anhui', 'city': 'hefei'}},
    'nico': {'name': 'nico', 'age': 26, 'birthday': datetime.strptime('1992-01-01', '%Y-%m-%d'),
             'address': {'province': 'beijing', 'city': 'beijing'}},
    'jane': {'name': 'jane', 'age': 23, 'birthday': datetime.strptime('1994-01-01', '%Y-%m-%d'),
             'address': {'province': 'shanghai', 'city': 'shanghai'}},
}

# 为 Person 资源构造解析器
# 给 GET/DELETE 请求的解析器
person_parser_get = reqparse.RequestParser(bundle_errors=True)
person_parser_get.add_argument('name', type=str, required=True, location='args', help='person name')
# 给 PUT/POST 请求的解析器
person_parser_body = person_parser_get.copy()
# person_parser_body.replace_argument('name', dest='name', type=str, required=True, location='json', help='person name')
person_parser_body.add_argument('age', type=inputs.int_range(1, 150), location='json', help='person age should in [1, 150]')
person_parser_body.add_argument('birthday', type=inputs.date, location='json', help='person birthday')
person_parser_body.add_argument('address', type=dict, location='json', help='person address')
# 要解析 嵌套的 address，需要再使用一个解析器，并使用 location 指定上面解析器 中的 address
person_address_parser = reqparse.RequestParser()
person_address_parser.add_argument('province', type=str, location=('address', ), help='person address.province')
person_address_parser.add_argument('city', type=str, location=('address', ), help='person address.province')
# 然后先解析验证上一层参数，再传入下一层 —— 也要在视图函数中解析
# person_args = person_parser_body.parse_args()
# person_address_args = person_address_parser.parse_args(req=person_args)

# Flask-restful 提供了 fields.XXX 类型指定 + marshal_with() 装饰器，用于格式化返回数据的结构
person_fields = {
    'name': fields.String,
    'age': fields.Integer,
    'birthday': fields.DateTime('iso8601'),
    'address': fields.Nested({
        'province': fields.String,
        'city': fields.String
    })
}

class Person(Resource):
    @marshal_with(person_fields)
    def get(self):
        args = person_parser_get.parse_args()
        name = args.name
        print('Person.GET name: ', name)
        if name in PERSON:
            p = PERSON[name]
            return p, 200
        else:
            return {}, 404

    @marshal_with(person_fields, envelope='person')  # envelope 表示是否用指定的 key 来对数据进行一层封装
    def post(self):
        args = person_parser_body.parse_args()
        address_args = person_address_parser.parse_args(req=args)
        name = args.name
        age = args.age
        birthday = args.birthday
        address = args.address
        province = address_args.province
        city = address_args.city
        print(f"<name: {name}, age: {age}, birthday: {birthday}, address: {address}, province: {province}, city: {city}")
        # return name, 200
        person = {'name': name, 'age': age, 'birthday': birthday, 'address': address}
        PERSON[name] = person
        return person, 200

    # 这里 PUT 的逻辑和 POST 一样
    @marshal_with(person_fields, envelope='person')
    def put(self):
        args = person_parser_body.parse_args()
        address_args = person_address_parser.parse_args(req=args)
        name = args.name
        age = args.age
        birthday = args.birthday
        address = args.address
        province = address_args.province
        city = address_args.city
        print(f"<name: {name}, age: {age}, birthday: {birthday}, address: {address}, province: {province}, city: {city}")
        person = {'name': name, 'age': age, 'birthday': birthday, 'address': address}
        PERSON[name] = person
        return person, 200

    @marshal_with(person_fields, envelope='person')
    def delete(self):
        args = person_parser_get.parse_args()
        name = args.name
        print('Person.DELETE name: ', name)
        if name in PERSON:
            p = PERSON.pop(name)
            return p, 200
        else:
            return {}, 404

api.add_resource(ParserTest, '/parser')
api.add_resource(Person, '/person')

