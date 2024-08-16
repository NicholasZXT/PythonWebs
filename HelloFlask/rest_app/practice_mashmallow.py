"""
练习 marshmallow 的使用.
"""
from datetime import date, datetime, timedelta
from marshmallow import Schema, fields, validate, validates, validates_schema, ValidationError, \
    pre_load, post_load, pre_dump, post_dump, INCLUDE, EXCLUDE, RAISE

"""
marshmallow使用起来，只需要重点关注如下两个对象：
+ Schema: 定义数据模型的基类
+ fields: 定义数据模型的具体字段
其他的辅助方法都是围绕着这两个对象进行的。
"""
class User:
    """ 定义一个用户类 """
    def __init__(self, name, gender, age, email, password):
        self.name = name
        self.gender = gender
        self.age = age
        self.email = email
        self.password = password
        self.created_at = datetime.now()

    def __repr__(self):
        return "<User(name={self.name!r}, gender={self.gender})>".format(self=self)

# 定义一个用户类对应的 Schema
class UserSchema(Schema):
    """
    使用 fields 提供的数据类型来做类型定义和校验，fields里所有数据类型的基类是 fields.Field，大部分的校验参数都可以参考此类的说明
    使用 validate.py 模块提供的校验类来设置校验规则
    """
    # ------ 字段定义 ------
    name = fields.String(
        required=True, allow_none=False,
        error_messages={"required": "Name is required."},
    )
    # Str() 是 String() 的别名
    gender = fields.Str(
        required=True, allow_none=False,
        validate=validate.OneOf(["male", "female"]),  # 也可以传入list，设置多个校验
        error_messages={"required": "gender is required."}
    )
    age = fields.Int(  # Int 也是 Integer 的别名
        required=False, allow_none=True,
        validate=validate.Range(min=1, max=120)
    )
    email = fields.Email(
        required=False, allow_none=True
    )
    password = fields.Str(
        required=False, allow_none=False,
        validate=validate.Length(min=4, max=10),
        load_default='12345',  # 只能在 required=False 字段上设置
        load_only=True,        # 表示此字段只有加载（反序列化）时使用，序列化时不会写出在结果里
    )
    created_at = fields.DateTime(
        required=False, allow_none=True,
        default=datetime.now(),
        # dump_only=True,  # 表示此字段只有在序列化时使用，反序列化时不会被加载——使用情况比较少见
    )
    # 嵌套模型可以使用如下方法，不过这里没有使用
    # nested_field = fields.Nested(OtherSchema)

    # ------ 检验方法 ------
    # 使用 validates 装饰器设置自定义校验单个字段的函数
    @validates("name")
    def validate_name(self, value):
        print(f"validate_name -> value: {value}")
        if len(value) > 30:
            raise ValidationError("name must less than 30 characters !")

    # 整个Schema对象级别的校验
    @validates_schema
    def validate_user(self, data, **kwargs):
        # data 就是校验过的数据dict
        print(f"validates_user_schema -> data: {data}")
        # 如果校验失败，需要在这里抛出 ValidationError，否则任何返回值都被视为校验成功

    # ------ 序列化：预处理/后处理相关的hook函数注册 ------
    # 序列化时各个hook函数执行顺序如下
    # @pre_dump(pass_many=False) methods
    # @pre_dump(pass_many=True) methods
    # dump(obj, many) (serialization)
    # @post_dump(pass_many=False) methods
    # @post_dump(pass_many=True) methods
    @pre_dump
    def pre_dump_user(self, data, **kwargs):
        print(f"pre_dump_user -> data: {data}")
        return data

    @post_dump
    def post_dump_user(self, data, **kwargs):
        print(f"post_dump_user -> data: {data}")
        return data

    # ------ 反序列化：预处理/后处理相关的hook函数注册 ------
    # 反序列化时各个hook函数执行顺序如下：
    # @pre_load(pass_many=True) methods
    # @pre_load(pass_many=False) methods
    # load(in_data, many) (validation and deserialization)
    # @validates methods (field validators)
    # @validates_schema methods (schema validators)
    # @post_load(pass_many=True) methods
    # @post_load(pass_many=False) methods
    @pre_load
    def pre_load_user(self, data, **kwargs):
        print(f"pre_load_user -> data: {data}")
        return data

    @post_load
    def post_load_user(self, data, **kwargs):
        """ 如果要返回 User 对象，通常需要在 post_load 回调函数里执行"""
        print(f"post_load_user -> data: {data}")
        # return data
        user = User(**data)
        return user

    # ------ 内部类，用于配置 ------
    class Meta:
        # 对于未知字段的处理，INCLUDE 表示包含进来，EXCLUDE 表示忽略，RAISE 表示抛出异常
        unknown = INCLUDE

# 还可以从dict中动态创建 Schema：
# UserSchemaV2 = Schema.from_dict(
#     {"name": fields.Str(), "email": fields.Email(), "created_at": fields.DateTime()}
# )


if __name__ == '__main__':
    user_schema = UserSchema()
    user1 = User(name="Daniel", gender='male', age=30, email="daniel@python.org", password='pwd')
    user2_dict = {'name': 'Jane', 'gender': 'female', 'age': 26, 'email': 'jane@python.org', 'password': 'pwd2'}
    user3_str = '{"name": "Someone", "gender": "female", "age": 20, "email": "someone@python.org", "password": "pwd3"}'
    # ------ 序列化 ------
    # dump 方法序列化成Python原生类型，通常是 dict
    s1 = user_schema.dump(user1)
    print(s1)
    # dumps 方法序列化成 JSON 字符串
    s2 = user_schema.dumps(user1)
    print(s2)
    # ------ 反序列化 ------
    # load 方法从 dict 等Python原生对象加载
    u1 = user_schema.load(user2_dict)
    # loads 方法从JSON字符串里加载
    u2 = user_schema.loads(user3_str)
    # 默认返回的 u1 和 u2 都是Python dict，如果要返回 User 对象就需要在 post_load 方法进行设置

    # ------ 反序列化校验错误示例 --------
    user4_dict = {'name': 'ErrorMan-saodjfioasdjfjasoijfoiasjiofioasd', 'gender': 'male', 'age': 26, 'email': 'jane@python.org', 'password': 'pwd2'}
    user5_dict = {'name': 'ErrorMan', 'gender': 'unknown', 'age': 26, 'email': 'jane@python.org', 'password': 'pwd2'}
    user6_dict = {'name': 'ErrorMan', 'gender': 'male', 'age': 130, 'email': 'jane@python.org', 'password': 'pwd2'}
    user7_dict = {'name': 'ErrorMan', 'gender': 'male', 'age': 25, 'email': 'jane@python.org', 'password': 'dsafiaosjfioajsifjisoajdofijioafjioasjofjioas'}
    try:
        u = user_schema.load(user4_dict)
        # u = user_schema.load(user5_dict)
        # u = user_schema.load(user6_dict)
        # u = user_schema.load(user7_dict)
    except ValidationError as e:
        print(f"e.valid_data: {e.valid_data}")
        print(f"e.messages: {e.messages}")
