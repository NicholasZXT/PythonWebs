from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from utils.database import Base


class User(Base):
    __tablename__ = "users"
    uid = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(length=50), nullable=False)
    gender = Column(String(length=16))

    def __repr__(self):
        return f"<User>-{{uid:{self.uid}, name:{self.name}, gender:{self.gender}}}"