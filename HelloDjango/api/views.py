from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
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
    serializer = StudentSerializer(student, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(http_method_names=['GET'])
# def list_student(request: Request):
def list_student(request: Request, format=None):
    print(request.method)
    students = Students.objects.all()
    serializer = StudentSerializer(students, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)
