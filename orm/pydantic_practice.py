"""
Pydantic使用练习
"""
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Person(BaseModel):
    uid: int | None = Field(default=None)
    # username 从定义上来看是可选的，但实际上username是必填的，除非设置 default=None ----------- KEY
    username: str | None = Field(min_length=1, max_length=20)
    gender: str | None = Field(default=None, choices=['male', 'female'])
    age: int | None = Field(default=None, ge=0, le=100)
    password: str | None = Field(default=None, repr=False, exclude=True)

    @model_validator(mode='after')
    def mask_uid(self):
        if self.uid is not None:
            print(f"uid shouldn't be set manually !")
            self.uid = None
        return self


p1 = Person(uid=1, username="zhangsan", gender="female", age=30, password="123456")
print(p1.model_dump())

# 直接调用 model_validate 方法校验
Person.model_validate({"uid": 1, "username": "zhangsan", "gender": "female", "age": 30, "password": "123456"})
Person.model_validate(p1)

# 校验异常
p2 = Person(uid=1, username="zhangsan", gender="female", age=-1, password="123456")

# 注意下面这个例子, username 没传，抛出的异常里显示:
# username
#   Field required [type=missing, input_value={'uid': 1, 'gender': 'fem...0, 'password': '123456'}, input_type=dict]
# 虽然 Person 类里的 username 定义时的参数类型是 str | None，看起来是可选的，但是 Pydantic 2 里面，这种方式仍然是必填的，只不过可以接受None
# 关于这一点的说明，参考官方文档 [Migration Guide -> Required, optional, and nullable fields](https://docs.pydantic.dev/dev/migration/#required-optional-and-nullable-fields)
p3 = Person(uid=1, gender="female", age=30, password="123456")
