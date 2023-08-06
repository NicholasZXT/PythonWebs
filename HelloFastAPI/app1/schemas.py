from pydantic import BaseModel

class UserItem(BaseModel):
    uid: int
    name: str
    gender: str
    is_activate: bool

    class Config:
        orm_mode = True