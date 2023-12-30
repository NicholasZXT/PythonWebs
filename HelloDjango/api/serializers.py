from rest_framework import serializers
from .models import Student, Teacher

# DRF 框架提供了多种序列化类

# 第1种，最基本的 Serializer 类，需要手动定义序列化用到的字段，并且可以提供更加精细的验证空值，但是代码比较繁琐
class StudentSerializer(serializers.Serializer):
    sid = serializers.IntegerField(read_only=True)  # sid 字段设置为只读，这样就无法通过POST或PUT请求提交相关数据进行反序列化
    name = serializers.CharField(max_length=50, required=True, allow_null=False)
    gender = serializers.CharField(max_length=50, required=True, allow_null=True)
    grade = serializers.CharField(max_length=50, required=True, allow_null=False)
    grade_class = serializers.CharField(max_length=50, required=False, allow_null=True)
    # 日期/日期时间字段可以通过 format 自定义输出格式
    create_date = serializers.DateField(read_only=True, format='%Y-%m-%d')

    def validate_gender(self, value):
        if value in ['male', 'female']:
            return value
        else:
            raise serializers.ValidationError('Invalid gender. gender value must in {male, female}')

    def create(self, validated_data):
        return Student.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.gender = validated_data.get('gender', instance.gender)
        instance.grade = validated_data.get('grade', instance.grade)
        instance.grade_class = validated_data.get('grade_class', instance.grade_class)
        instance.save()
        return instance

# 第2种，ModelSerializer，可以自动从对应的Model中读取设置字段，自动生成序列化的验证器，并且实现了简单的 .create() 和 .update() 方法
class TeacherSerializer(serializers.ModelSerializer):
    # 手动设置日期字段的序列化信息，主要是设置日期格式
    create_date = serializers.DateField(read_only=True, format='%Y-%m-%d')

    # 这种序列化器只需要定义下面的元数据信息
    class Meta:
        model = Teacher
        fields = '__all__'
        read_only_fields = ('tid', 'create_date')

    def validate_gender(self, value):
        if value in ['male', 'female']:
            return value
        else:
            raise serializers.ValidationError('Invalid gender. gender value must in {male, female}')
