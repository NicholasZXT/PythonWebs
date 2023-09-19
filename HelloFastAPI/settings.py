mysql_conf = {
    'user': 'root',
    'passwd': 'mysql2022',
    'host': 'localhost',
    'port': 3306,
    'db': 'hello_fastapi'
}
DB_URL = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}".format(**mysql_conf)

SECRET_KEY = "fastkey09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf68e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 10

AUTHORIZED_USERS = {
    'admin': {'passwd': 'admin', 'roles': ['admin']},
    'yourself': {'passwd': 'people', 'roles': ['others']},
}