from pydantic import BaseModel

class UserItem(BaseModel):
    uid: int | None = None  # 设置默认值，这样创建用户的时候，就不需要传入uid的值，让数据库自动生成
    name: str
    gender: str

    # 这个配置告诉 pydantic 的模型，数据是从ORM对象中获取的
    class Config:
        orm_mode = True