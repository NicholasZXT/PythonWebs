import logging
import peewee as pw
from datetime import datetime, timedelta

# peewee 的日志设置
logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

# ================= Database =================
def P1_DataBase():
	pass
# -------- 创建 Database 对象 --------
# 除此之外，还支持 SqliteDatabase, PostgresqlDatabase
# 第 1 种，创建对象时直接传入数据库配置
db = pw.MySQLDatabase(database='crashcourse', user='root', password='mysql2020', host='localhost', port=3306)
# 第 2 种，先创建对象，后使用数据库配置初始化
# db = pw.MySQLDatabase()
# db.init(database='crashcourse', user='root', password='mysql2020', host='localhost', port=3306)
# 第 3 种，动态定义，这时候要使用代理对象
# db_proxy = pw.DatabaseProxy()
# db_type = 'mysql'
# if db_type == 'mysql':
# 	db = pw.MySQLDatabase()
# else:
# 	db = pw.SqliteDatabase()
# db_proxy.initialize(db)

# -------- 建立、关闭连接 --------
db.connect()           # 返回True 或者 False
con = db.connection()  # 获取连接对象
print(type(con))
# <class 'pymysql.connections.Connection'>
db.close()             # 返回True 或者 False
# 如果在 open 的db上执行 connect，会抛异常，一个办法是使用下面的参数
# con = db.connect(reuse_if_open=True)
# 也可以在创建 db 的时候，参数里指定 autoconnect=True

# -------- 结合 with 上下文管理器使用 --------
# 第 1 种：自动管理事务
print("before: ", db.is_closed())
with db:
	print("with: ", db.is_closed())
print("after: ", db.is_closed())
# 第 2 种：手动管理
print("before: ", db.is_closed())
with db.connection_context() as con:
	print("con: ", con)
	print("with: ", db.is_closed())
print("after: ", db.is_closed())
# 或者以装饰器的方式使用
@db.connection_context()
def prepare_database():
	pass

# -------- 事务管理 --------
# 第 1 种，使用 with 上下文管理
with db.atomic() as transaction:
	try:
		print("in transaction")
	except Exception as e:
		print("failed")
		transaction.rollback()
# 第 2 种，使用装饰器
@db.atomic()
def create_something():
	pass


# ================= Model =================
def P2_Model():
	pass

# -------- Model定义 --------
class Person(pw.Model):
	# id = pw.IntegerField(primary_key=True)  # 没有定义主键的情况下，会自动生成这个主键
	uid = pw.AutoField(primary_key=True)  # 自定义主键
	name = pw.CharField(max_length=127, null=False, index=True, verbose_name="姓名", help_text="help info: 姓名")
	age = pw.IntegerField(null=True, verbose_name="年龄")
	gender = pw.CharField(max_length=127, null=True, verbose_name="性别")
	# 不能使用 update 作为名称，因为它和 Model 的方法名冲突了，这时候就需要使用 column_name
	update_ = pw.TimestampField(column_name='update', null=True)
	# 上述 Field 中，还可以使用如下参数：
	# default=，设置默认值
	# column_name=，显式指定表中对应的字段，默认下就是属性名

	# 但是似乎不能创建字段的注释和表注释？？？

	# 记录表的元数据
	class Meta:
		# 关联的数据库对象，这个操作也可以后面进行
		database = db
		table_name = 'person'
		# 指定复合主键
		# primary_key = pw.CompositeKey('uid', 'name')
		# primary_key = False # 也可以指定无主键
		# 其他设置
		table_settings = []
		# 其他参数，用于table extensions
		options = {}

# -------- Model 访问 --------
# 创建之后，访问 Meta，不是通过 .Meta 访问
print(Person._meta)
print(Person._meta.fields)
print(Person._meta.database)
print(Person._meta.table_name)

# -------- 建表 --------
with db:
	db.create_tables(models=[Person])

# -------- 数据库和表绑定 --------
# 除了定义Model的时候在 Meta 里通过 database= 来关联表对应的数据库，也可以通过下面的方式
# 第 1 种
db.bind(models=[Person])
# 第 2 种
with db.bind_ctx([Person]):
	print("do some CRUD")
# 第 3 种
Person.bind(database=db)
# 第 4 种
with Person.bind_ctx(db, bind_backrefs=False):
	assert Person._meta.database is db


# ================= Model =================
def P3_CRUD():
	pass

# -------- 插入 --------
def P3_1_Add():
	"""
	插入语句通过 Model.create() 方法
	"""
	# 创建后直接插入，并返回创建的对象
	p1 = Person.create(uid=1, name="daniel", age=20, gender="male", update_=datetime.now())
	print(type(p1))  # p1 是 Person 对象

	# 直接插入，不返回创建的对象，返回的是影响的行数
	# affect_num = Person.insert(uid=1, name="daniel", age=20, gender="male", update_=datetime.now())

	# 下面这种实际上是 update
	p2 = Person(uid=2, name="jane", age=18, gender="female", update_=datetime.now())
	p2.save()

	# 批量插入
	with (db.atomic()):
		# 注意结尾的 .execute() 方法
		Person.insert_many(rows=[
			{"uid": 3, "name": "xiaoming", "age": 25, 'gender': 'male'},
			{"uid": 4, "name": "xiaohong", "age":26, 'gender': 'female'}
		]
		).execute()


# -------- 更新 --------
def P3_2_Update():
	"""
	更新语句通过 Model.save() 方法
	"""
	p1 = Person(uid=3, name="jane", age=18, gender="female", update_=datetime.now())
	p1.save()


# -------- 删除 --------
def P3_3_Delete():
	p1 = Person(uid=4, name="xiaohong", age=18, gender="female", update_=datetime.now())
	# 实际上是按主键删除
	p1.delete_instance()


# -------- 查询 --------
def P3_4_Query():
	# 查询单个记录
	p1 = Person.get_by_id('1')
	print(p1)
	print(p1.name)
	print(p1.age)
	print(p1.gender)

	# 未查询到则抛异常
	p2 = Person.get(Person.uid == 3)
	print(p2.uid)
	print(p2.name)

	# 未查询到时返回None，而不是抛异常
	p2 = Person.get_or_none(Person.uid == 3)

	# select 查询
	for p in Person.select():
		print(f"uid: {p.uid}, name: {p.name}, gender: {p.gender}, age: {p.age}")

	res = Person.select().where(Person.age >= 20, Person.gender == 'male').order_by(Person.age.desc())
	for p in res:
		print(f"uid: {p.uid}, name: {p.name}, gender: {p.gender}, age: {p.age}")

	# 聚合
	res = Person.select(Person.gender, pw.fn.COUNT(Person.uid).alias('cnt')) \
		.group_by(Person.gender) \
		.order_by(pw.fn.COUNT(Person.uid).desc())
	for p in res:
		print(f"gender: {p.gender}, cnt: {p.cnt}")
