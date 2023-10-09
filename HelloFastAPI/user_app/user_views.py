from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from dependencies.database_dep import get_db
from .models import User
from .schemas import UserItem, UserResponse
from user_app import crud_actions

user_router = APIRouter(tags=['User-App'])

@user_router.post("/users/", response_model=UserItem)
def create_user(user: UserItem, db: Session = Depends(get_db)):
    # user 是 UserItem 对象，由于它是一个 pydantic.BaseModel 子类，会从 post 请求体中自动解析
    # db 是通过依赖传入的 sqlalchemy 连接对象 Session
    db_user = crud_actions.get_user(db, uid=user.uid)
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    new_user = crud_actions.create_user(db=db, user_item=user)
    # 这里返回的 new_user 是 sqlalchemy 的 Model 子类 User 的对象，和 response_model 参数指定的 UserItem 不是一个类，
    # 但是由于 response_model 指定了返回的模型是 UserItem，并且 UserItem 的定义里有 orm_mode = True 这个配置，
    # 所以可以直接返回 User 对象，FastAPI 会自动完成JSON序列化，下面的几个接口同样如此
    return new_user

@user_router.get("/users/{user_id}", response_model=UserItem)
def get_user(user_id: int, uid: int = 1, db: Session = Depends(get_db)):
    # user_id 和 URL 中的 {user_id} 同名，所以它是一个 路径参数 —— 需要从 URL 路径中获得
    # uid 不在路径参数中，所以会从查询参数中解析 —— 也就是位于 URL 的 ？ 之后，并以 & 符号分隔的键值对参数
    db_user = crud_actions.get_user(db, uid=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@user_router.get("/list_users", response_model=list[UserItem])
def list_users(db: Session = Depends(get_db)):
    users = crud_actions.list_users(db)
    # user_items = [UserItem(uid=user.uid, name=user.name, gender=user.gender, is_active=user.is_active) for user in users]
    return users


# ----------------- 以下的接口直接在视图函数内完成 ORM 操作，就不放到 crud_actions.py 文件里了 -------------------------

@user_router.get("/list_genders", response_class=JSONResponse)
def list_genders(db: Session = Depends(get_db)):
    """
    显示有哪些性别. \n
    只是为了展示 distinct 的用法。
    """
    genders = db.query(User.gender).distinct().all()
    res = [item.gender for item in genders]
    return {'genders': res}

@user_router.get("/filter_user", response_model=UserResponse)
def filter_users(db: Session = Depends(get_db), page_size: int = 20, page_index: int = 1, gender: str = None):
    """
    展示分页+过滤查询
    """
    if page_index <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_index should > 0")
    if gender is not None and len(gender) > 0:
        total = db.query(func.count(User.uid)).filter(User.gender == gender).scalar()
        res = db.query(User.name, User.gender)\
            .filter(User.gender == gender) \
            .order_by(User.uid)\
            .limit(page_size).offset((page_index-1)*page_size).all()
    else:
        total = db.query(func.count(User.uid)).scalar()
        res = db.query(User.name, User.gender)\
            .order_by(User.uid)\
            .limit(page_size).offset((page_index-1)*page_size).all()
    # 由于不想展示 uid 字段，返回的 res 里是一个 Row 对象而不是 User 对象，需要手动组装成 UserItem 对象
    data = [UserItem(**item) for item in res]
    # 直接返回 dict 的话，会使用 JSONResponse 进行序列化，但是 data 中的 UserItem 对象会序列化失败
    # return {'page_index': page_index, 'page_size': page_size, 'total': total, 'gender'=gender, data: data}
    # 需要使用自定义的嵌套 pydantic.BaseModel 子类 UserResponse 来告诉 FastAPI 如何进行序列化
    return UserResponse(page_index=page_index, page_size=page_size, total=total, gender=gender, data=data)
