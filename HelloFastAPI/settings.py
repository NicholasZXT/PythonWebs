mysql_conf = {
    'user': 'root',
    'passwd': 'mysql2022',
    'host': 'localhost',
    'port': 3306,
    'db': 'hello_fastapi'
}
DB_URL = "mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}".format(**mysql_conf)