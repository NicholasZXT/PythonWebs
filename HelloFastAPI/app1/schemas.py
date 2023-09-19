"""
使用 pydantic 定义 请求模型 或者 返回模型
"""
from typing import List
from pydantic import BaseModel

class UserItem(BaseModel):
    uid: int | None = None  # 设置默认值，这样创建用户的时候，由于uid是自增主键，就不需要传入uid的值，让数据库自动生成
    name: str
    gender: str

    # 这个配置告诉 pydantic 的模型，数据是从 ORM 对象中获取的
    class Config:
        orm_mode = True

# 专门用于展示用户返回结果的 Model，
class UserResItem(BaseModel):
    # uid: int | None = None  # uid 一般不需要展示，所以这里少了这个字段
    name: str
    gender: str

    # 这个配置告诉 pydantic 的模型，数据是从 ORM 对象中获取的
    class Config:
        orm_mode = True

# 定义返回的 嵌套Response 模型
class UserResponse(BaseModel):
    total: int
    page_index: int
    page_size: int
    gender: str | None = None
    data: List[UserResItem]  # 这里使用的是用于封装返回结果的 User

    class Config:
        orm_mode = True
