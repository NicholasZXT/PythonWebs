'''
用于展示 DRF 框架序列化器的使用
'''
# import os
# print("CWD: ", os.getcwd())
# os.chdir('HelloDjango')
# print("CWD: ", os.getcwd())
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'ideablog.settings.dev')
import io
import json
from django.db import models
from rest_framework import serializers
# 配置Django的setting环境——只能执行一次
from django.conf import settings
settings.configure()
# 不能直接在ipython中导入下面两个包，需要按照上面的方式配置Django的SETTINGS，或者在 django shell 中执行
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

class Person:
    def __init__(self, name, gender):
        self.name = name
        self.gender = gender

    def __str__(self):
        return f"{{name: {self.name}, gender: {self.gender}}}"


class PersonSerializerV1(serializers.Serializer):
    name = serializers.CharField(max_length=63)
    gender = serializers.CharField(max_length=15)


p1 = Person(name='XiaoMing', gender='male')
p2 = Person(name='XiaoHong', gender='female')
print(p1)

# 1. 序列化对象
# 序列化时使用的参数名是 instance=
s1 = PersonSerializerV1(instance=p1)
print(s1.data)
print(type(s1.data))
# 序列化成 bytes 对象
p1_bytes = JSONRenderer().render(s1.data)
print(p1_bytes)
# 相当于下面的操作
# p1_bytes = json.dumps(s1.data).encode()

# 序列化多个对象
s12 = PersonSerializerV1([p1, p2], many=True)
print(s12)

# 2. 反序列化对象
# 首先要将 bytes 解析成 dict
stream = io.BytesIO(p1_bytes)
p1_ = JSONParser().parse(stream)
# 上面几句相当于下面
# p1_ = json.loads(p1_bytes)
print(type(p1_))  # 是个dict
# 使用 解析成 dict 的数据进行反序列化，注意，此时参数名是 data=
s1_rev = PersonSerializerV1(data=p1_)
# 不能一开始就访问 .data，会报错，必须要先调用 .is_valid() 方法检验数据
# print(s1_rev.data)
# 但是可以访问 .initial_data
print(s1_rev.initial_data)
# 必须先验证数据
print(s1_rev.is_valid())
# 结果为 True 之后，再访问 data
print(s1_rev.data)
print(type(s1_rev.data))  # 类型是 <class 'rest_framework.utils.serializer_helpers.ReturnDict'>
# 验证后的结果存放在 .validated_data 里
print(s1_rev.validated_data)
print(type(s1_rev.validated_data))   # 类型是 <class 'collections.OrderedDict'>

# 由于 PersonSerializerV1 没有实现 .create() 方法，这里会 NotImplementedError
s1_rev_obj = s1_rev.save()

# 对于 .is_valid() 为 False 的情况，错误信息存放在 .errors 中
s1_rev = PersonSerializerV1(data=p1_bytes)
print(s1_rev.is_valid())
print(s1_rev.validated_data)   # 此时为空数据
print(s1_rev.data)             # 这个也是空dict
# 查看具体的错误信息
print(s1_rev.errors)
print(s1_rev.error_messages)


# 到这一步，只是将验证后的各个字段恢复成原生的python数据类型，并存入了一个 dict 中，但是还没有得到 Person 对象

# ----------------------------------------------------------------------------------------------------------------------
# 如果要反序列化获得 Person 对象，还需要实现 Serializer 子类中的 .create() 或者 .update() 方法
class PersonSerializerV2(serializers.Serializer):
    name = serializers.CharField(max_length=63)
    gender = serializers.CharField(max_length=15)

    def create(self, validated_data):
        """
        根据验证过的数据创建并返回一个新的实例对象.
        validated_data 参数就是上面 Serializer.validated_data 属性.
        """
        return Person(**validated_data)

    def update(self, instance, validated_data):
        """
        根据验证过的数据更新和返回一个已经存在的实例对象。
        instance 参数就是创建此序列化类时传入的实例对象.
        validated_data 参数就是上面 Serializer.validated_data 属性.
        """
        instance.name = validated_data.get('name', instance.name)
        instance.gender = validated_data.get('gender', instance.gender)
        return instance


s2 = PersonSerializerV2(instance=p2)
s2_bytes = JSONRenderer().render(s2.data)
s2_ = json.loads(s2_bytes)
print(s2_)
# 开始反序列化
s2_rev = PersonSerializerV2(data=s2_)   # 这里只使用了 data 参数，没有传入 instance 参数，表示此时反序列化创建一个新对象
print(s2_rev.is_valid())
print(s2_rev.validated_data)
# 拿到反序列化后的 Person 对象
s2_rev_person = s2_rev.save()
print(s2_rev_person)
print(type(s2_rev_person))  # 现在是 <class 'Person'> 类型了

# 如果要更新一个对象，可以使用下面的方式
p3 = Person(name='Li', gender='male')
p3_update = {'name': 'Li_new', 'gender': 'neutral'}  # 这里的字段能否缺失要看 PersonSerializerV2 里每个 field 的配置
# instance 是需要被更新的实例对象， data 是更新的数据
s3 = PersonSerializerV2(instance=p3, data=p3_update)
print(s3.is_valid())
# print(s3.errors)
# 此时调用 .save()，得到的就是更新后的对象了
s3_update = s3.save()
print(s3_update)
print(type(s3_update))
# 当然，也可以手动调用 .update() 方法——但是只能调用一次
# print(s3.update())


# ----------------------------------------------------------------------------------------------------------------------
# 上述的字段验证是在 Serializer 的 Field 里默认定义的，一般只能验证类型或者空值，如果要控制各个字段的验证逻辑，
# 可以创建一个 .validate_<field_name> 的方法
class PersonSerializerV3(serializers.Serializer):
    name = serializers.CharField(max_length=63)
    gender = serializers.CharField(max_length=15)
    # 如果 required=False，那么下面的验证函数就不会被执行
    # gender = serializers.CharField(max_length=15, required=False)

    def create(self, validated_data):
        return Person(**validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.gender = validated_data.get('gender', instance.gender)
        return instance

    def validate_gender(self, value):
        """
        用于自定义 gender 字段的验证逻辑，value 就是传入的验证的值
        """
        if value in {'male', 'female'}:
            return value
        else:
            raise serializers.ValidationError("gender value must in {male, female}")


s4_data = {'name': 'WangWang', 'gender': 'neutral'}
s4 = PersonSerializerV3(data=s4_data)
print(s4.is_valid())
print(s4.errors)  # {'gender': [ErrorDetail(string='gender value must in {male, female}', code='invalid')]}


# ----------------------------------------------------------------------------------------------------------------------
# 上述的序列化/反序列化过程，都是针对普通的Python类进行的，如果要和 Django 的 models 结合起来，只需要在 .create() 和 .update() 方法里操作
class PersonModel(models.Model):
    name = models.CharField(max_length=50, verbose_name='姓名')
    gender = models.CharField(max_length=15, verbose_name='性别')

class PersonSerializerV4(serializers.Serializer):
    name = serializers.CharField(max_length=63)
    gender = serializers.CharField(max_length=15)

    # 下面两个标 KEY 的地方，是唯一区别于普通python类的地方，也就是只是加入了一些 Model 的操作而已

    def create(self, validated_data):
        # return Person(**validated_data)
        # 改为使用 Model 创建一个新的用户实例对象
        return PersonModel.objects.create(**validated_data)      # -------- KEY

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.gender = validated_data.get('gender', instance.gender)
        # 这里调用的是 Model 的 save() 方法
        instance.save()           # ------------- KEY
        return instance

    def validate_gender(self, value):
        """
        用于自定义 gender 字段的验证逻辑，value 就是传入的验证的值
        """
        if value in {'male', 'female'}:
            return value
        else:
            raise serializers.ValidationError("gender value must in {male, female}")
