"""
Pydantic使用练习
"""
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from datetime import datetime
import re


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


class Policy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(required=True)
    title: str = Field(required=True)
    pubDate: str | None = Field(default=None, validation_alias="pub_date")
    pubNum: str | None = Field(default=None, validation_alias="doc_num")
    institution: str | None = Field(default=None, validation_alias="org")
    province: str | None = Field(default=None)
    level: str | None = Field(default=None)
    industry: str | None = Field(default=None)
    topic: str | None = Field(default=None, validation_alias="theme")
    target: str | None = Field(default=None)
    motivation: str | None = Field(default=None)
    category: str | None = Field(default='政策文件')
    url: str = Field(required=True)
    content: str = Field(required=True)
    source: str = Field(default='import')
    # createdAt: str = Field()
    # updatedAt: str = Field()

    @field_validator('org', mode='before')
    @classmethod
    def validate_institution(cls, value: Dict[str, str]) -> str:
        keys = list(value.keys())
        return ','.join(keys)

    @field_validator('pub_date', mode='after')
    @classmethod
    def validate_pubdate(cls, value: str) -> str | None:
        """
        将不同格式的日期字符串统一转换为 yyyy-mm-dd 格式
        支持的格式:
        - 2025-07-01
        - 2025-07-01 12:00:00
        - 2025年6月15号
        Args:
            date_str (str): 输入的日期字符串
        Returns:
            str: 格式化后的日期字符串 (yyyy-mm-dd)
        """
        if not value:
            return None
        # 处理 2025-07-01 12:00:00 这种带时间的格式，只取日期部分
        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', value):
            return value.split(' ')[0]
        # 处理标准的 2025-07-01 格式
        if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return value
        # 处理 2025年6月15号 这种中文格式
        chinese_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})号?'
        match = re.match(chinese_pattern, value)
        if match:
            year, month, day = match.groups()
            # 确保月份和日期是两位数格式
            return f"{year}-{int(month):02d}-{int(day):02d}"
        # 如果都不匹配，尝试使用 datetime 解析
        try:
            # 尝试常见格式
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        except Exception:
            pass
        # 如果所有格式都无法解析，返回原字符串
        return value


if __name__ == '__main__':
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
