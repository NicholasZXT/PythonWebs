from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.

# 使用Django自带的用户模型
# User = get_user_model()

class Student(models.Model):
    # 定义字段
    sid = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name='姓名', db_comment='姓名')
    gender = models.CharField(max_length=50, verbose_name='性别', db_comment='性别')
    grade = models.CharField(max_length=50, verbose_name='年级', db_comment='年纪')
    grade_class = models.CharField(max_length=50, verbose_name='班级', db_comment='班级')
    # created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间', db_comment='创建时间')
    create_date = models.DateField(auto_now_add=True, verbose_name='创建时间', db_comment='创建时间')

    # 表的元数据信息通过一个内部类 Meta 来设置，这些元数据信息也是可选的
    class Meta:
        managed = True   # 是否交由 ORM 框架管理，默认为True
        # db_tablespace = 'dbbase'   # 数据库
        db_table = 'api_student'             # 设置表名称，默认下Django会以全小写的 {app_name}_{model_class_name} 形式创建表
        db_table_comment = '学生信息表'        # 设置表的注释, 4.2版本开始才有这个功能
        verbose_name = '学生信息表'            # 此Model的文本表示，用于在 Admin 界面显示等
        verbose_name_plural = verbose_name   # 复数形式，默认下会在 verbose_name 后面加上字符串 s 表示复数（比如在Admin界面显示时）
        ordering = ['name', '-grade']        # 指定数据记录的排序字段，默认ASC，- 表示 DESC
        # 定义索引字段
        # indexes = [models.Index(fields=["name"])]


class Teacher(models.Model):
    # 定义字段
    tid = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name='姓名', db_comment='姓名')
    gender = models.CharField(max_length=50, verbose_name='性别', db_comment='性别')
    subject = models.CharField(max_length=50, verbose_name='学科', db_comment='学科')
    grade = models.CharField(max_length=50, verbose_name='年级', db_comment='年级')
    grade_class = models.CharField(max_length=50, verbose_name='班级', db_comment='班级')
    create_date = models.DateField(auto_now_add=True, verbose_name='创建时间', db_comment='创建时间')

    # 表的元数据信息通过一个内部类 Meta 来设置，这些元数据信息也是可选的
    class Meta:
        managed = True   # 是否交由 ORM 框架管理，默认为True
        # db_tablespace = 'dbbase'   # 数据库
        db_table = 'api_teacher'              # 设置表名称，默认下Django会以全小写的 {app_name}_{model_class_name} 形式创建表
        db_table_comment = '教师信息表'         # 设置表的注释, 4.2版本开始才有这个功能
        verbose_name = '教师信息表'             # 此Model的文本表示，用于在 Admin 界面显示等
        verbose_name_plural = verbose_name    # 复数形式，默认下会在 verbose_name 后面加上字符串 s 表示复数（比如在Admin界面显示时）
        ordering = ['name', '-subject']       # 指定数据记录的排序字段，默认ASC，- 表示 DESC
