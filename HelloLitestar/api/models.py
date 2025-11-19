from typing import TYPE_CHECKING, Annotated
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from litestar.dto import AbstractDTO, DTOConfig, DataclassDTO, DTOData, DTOField, dto_field
from litestar.plugins.pydantic import PydanticDTO
# from litestar.plugins.sqlalchemy import SQLAlchemyDTO


class User(BaseModel):
    uid: Annotated[UUID, Field(title="用户ID", default_factory=uuid4)]
    name: Annotated[str, Field(title="用户名称", max_length=20, min_length=2)]
    email: Annotated[str, Field(title="用户邮箱", max_length=50, min_length=5)]
    age: Annotated[int, Field(title="年龄", ge=0, le=100)]
    passwd_hash: Annotated[str | None, Field(title="密码", max_length=128, min_length=6)] = None


class UserWriteDTO(PydanticDTO[User]):
    config = DTOConfig(exclude={"id"})


class UserReadDTO(PydanticDTO[User]):
    config = DTOConfig(exclude={"passwd_hash"})
