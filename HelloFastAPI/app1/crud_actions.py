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
    user = User(name=user_item.name, gender=user_item.gender, is_active=user_item.is_activate)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
