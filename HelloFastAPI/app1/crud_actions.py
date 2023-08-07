from sqlalchemy.orm import Session
from .models import User
from .schemas import UserItem

def list_users(db: Session):
    users = db.query(User).limit(10).all()
    return users

def get_user(db: Session, uid: int):
    user = db.query(User).filter_by(uid=uid).first()
    return user

def create_user(db: Session, user_item: UserItem):
    user = User(name=user_item.name, gender=user_item.gender)
    db.add(user)
    db.commit()
    db.refresh(user)
    print("create_user: ", user)
    return user
