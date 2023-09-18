from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from utils.database import SessionLocal, engine
# from utils.database import Base
from .models import Base
from .schemas import UserItem
from app1 import crud_actions

def create_db_tables():
    Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    # 在依赖中使用yield时，yield之后的代码会在每次请求对应的视图函数返回 Response 之后执行，刚好用来做收尾工作
    finally:
        db.close()


user_router = APIRouter()

@user_router.post("/users/", response_model=UserItem)
def create_user(user: UserItem, db: Session = Depends(get_db)):
    # db 是通过依赖传入的 sqlalchemy 的连接 session
    db_user = crud_actions.get_user(db, uid=user.uid)
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    new_user = crud_actions.create_user(db=db, user_item=user)
    # 这里返回的 new_user 是 sqlalchemy 的 Model 子类 User 的对象，和 response_model 参数指定的 UserItem 不是一个类，但是由于
    # UserItem 的定义里有 orm_mode = True 这个配置，所以可以解析，下面的几个接口同样如此
    return new_user

@user_router.get("/users/{user_id}", response_model=UserItem)
def read_user(uid: int, db: Session = Depends(get_db)):
    db_user = crud_actions.get_user(db, uid=uid)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@user_router.get("/users/", response_model=list[UserItem])
def read_users(db: Session = Depends(get_db)):
    users = crud_actions.list_users(db)
    return users
    # user_items = [UserItem(uid=user.uid, name=user.name, gender=user.gender, is_active=user.is_active) for user in users]
