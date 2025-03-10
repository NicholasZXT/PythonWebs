from pydantic import BaseModel
from typing import Union, List

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: str

class AuthUser(BaseModel):
    username: str
    roles: List[str] = None
    disabled: Union[bool, None] = False
