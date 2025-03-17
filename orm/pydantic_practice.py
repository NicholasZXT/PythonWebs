"""
Pydantic使用练习
"""
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Person(BaseModel):
    uid: int | None = Field(default=None)
    username: str | None = Field(default=None, min_length=1, max_length=20)
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
p1 = Person(uid=1, username="zhangsan", gender="female", age=-1, password="123456")
