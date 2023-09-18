from typing import Union
from pydantic import BaseModel

class TokenData(BaseModel):
    access_token: str
    token_type: str
    expires_in: str


class User(BaseModel):
    username: str
    email: str | None = None
    disabled: bool | None = None