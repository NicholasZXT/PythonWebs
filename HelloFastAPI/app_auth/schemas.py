from typing import Union
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: str

class User(BaseModel):
    username: str
    disabled: bool | None = None