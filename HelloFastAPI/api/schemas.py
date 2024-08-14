from pydantic import BaseModel, Field
from typing import Union, Optional
from enum import Enum

class Gender(str, Enum):
    male = 'male'
    female = 'female'

class ItemBody(BaseModel):
    id: int
    name: str
    used: Optional[bool] = False  # 可选字段

class UserBody(BaseModel):
    uid: int
    name: str
    age: int = Field(default=None, ge=0, le=100, title='年龄', description='用户年龄（0~100）')
    # gender: Optional[str] = None
    gender: Optional[Gender] = None  # 枚举类型
