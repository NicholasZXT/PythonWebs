from typing import TYPE_CHECKING
from dataclasses import dataclass
from uuid import UUID
from pydantic import BaseModel, EmailStr


@dataclass
class MockToken:
    api_key: str


@dataclass
class MockUser:
    name: str


class User(BaseModel):
    # uid: UUID
    uid: str
    name: str
    age: int
    role: str
    # email: EmailStr

