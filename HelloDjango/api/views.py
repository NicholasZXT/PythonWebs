from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .models import Students, Teachers
from .serializers import StudentSerializer, TeacherSerializer

# Create your views here.

@api_view(http_method_names=['GET'])
# def get_student(request: Request, sid):
def get_student(request: Request, sid, format=None):
    print('sid: ', sid)
    # params = request.query_params
    # print(params)
    student = Students.objects.all().filter(sid=sid)
    print(student)
    # 这里即使上面返回的只有一个student的数据，也要使用 many=True
    # 使用序列化器的 instance 参数，表示此时对数据执行序列化
    serializer = StudentSerializer(instance=student, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(http_method_names=['GET'])
# def list_student(request: Request):
def list_student(request: Request, format=None):
    print(request.method)
    students = Students.objects.all()
    serializer = StudentSerializer(instance=students, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(http_method_names=['POST'])
def create_student(request: Request):
    # 主要是从POST请求体的JSON中解析
    print(request.data)
    # 从请求中解析出待序列化的对象
    data = JSONParser().parse(request)
    # 使用 data 参数，表示对数据执行反序列化过程
    serializer = StudentSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)
