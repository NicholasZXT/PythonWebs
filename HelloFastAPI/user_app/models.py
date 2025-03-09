"""
使用 SQL-Alchemy 定义 ORM 用到的表模型
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {
        'mysql_engine': 'InnoDB',
        'comment': 'FastAPI-用户测试表',
        # 下面的这个属性是为了让 User 可以修改，重复定义，否则修改字段后，重新生成此类时，Base 类不允许重新注册已存在的类
        'extend_existing': True
    }
    uid = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(length=50), nullable=False)
    gender = Column(String(length=16))

    def __repr__(self):
        return f"<User>-{{uid:{self.uid}, name:{self.name}, gender:{self.gender}}}"


if __name__ == '__main__':
    # 测试 SQLAlchemy 的 ORM 使用
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import func
    mysql_conf = {
        'user': 'root',
        'passwd': 'mysql2022',
        'host': 'localhost',
        'port': 3306,
        'db': 'hello_fastapi'
    }
    db_url = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}".format(**mysql_conf)
    engine = create_engine(url=db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # genders = db.query(User.gender).distinct().all()
    # row = genders[0]
    # print(row.gender)

    # total = db.query(func.count(User.uid)).scalar()
    # total_part = db.query(func.count(User.uid)).filter(User.gender == "male").scalar()
    # res = db.query(User).order_by(User.uid).limit(5).offset(3).all()
    # res_part = db.query(User.name, User.gender).order_by(User.uid).limit(5).offset(3).all()
    # row1 = res[0]
    # row2 = res_part[0]
    # print(row1)
    # print(row2)
