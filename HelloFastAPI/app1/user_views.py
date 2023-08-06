from fastapi import APIRouter, Depends,HTTPException
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
    finally:
        db.close()


user_router = APIRouter()

@user_router.post("/users/", response_model=UserItem)
def create_user(user: UserItem, db: Session = Depends(get_db), ):
    db_user = crud_actions.get_user(db, uid=user.uid)
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    return crud_actions.create_user(db=db, user_item=user)

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
