from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, CreateModelMixin
from rest_framework.generics import GenericAPIView, ListCreateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .models import Student, Teacher
from .serializers import StudentSerializer, TeacherSerializer

# Create your views here.
"""
DRF对Django进行了如下的扩展：
1. rest_framework.request.Request 是对  django.http.request.HttpRequest 的扩展，提供了更加方便的使用方式，特别是 Request.data
2. rest_framework.response.Response 是对  django.http.response.HttpResponse 的扩展
3. rest_framework.status 里定义了许多HTTP状态码的常量，比如 HTTP_404_NOT_FOUND = 404，方便使用
4. rest_framework.decorators.api_view 提供了定义视图函数的简便方式；而 rest_framework.views.APIView 提供了class-based views封装
"""

# =============== 基于函数的视图 =================
@api_view(http_method_names=['GET'])
# def get_student(request: Request, sid):
def get_student(request: Request, sid, format=None):
    print('get_student - sid: ', sid)
    # params = request.query_params
    # print(params)
    student = Student.objects.all().filter(sid=sid)
    print(student)
    # 这里即使上面返回的只有一个student的数据，也要使用 many=True
    # 使用序列化器的 instance 参数，表示此时对数据执行序列化
    serializer = StudentSerializer(instance=student, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(http_method_names=['GET'])
# def list_student(request: Request):
def list_student(request: Request, format=None):
    print('list_student: ', request.method)
    students = Student.objects.all()
    serializer = StudentSerializer(instance=students, many=True)
    return Response(data=serializer.data, status=status.HTTP_200_OK)

@api_view(http_method_names=['POST'])
def create_student(request: Request):
    # 主要是从POST请求体的JSON中解析
    print('create_student - data: ', request.data)
    # 从请求中解析出待序列化的对象
    # data = JSONParser().parse(request)  # 这一句有问题
    data = request.data
    # 使用 data 参数，表示对数据执行反序列化过程
    serializer = StudentSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


# =============== 基于类的视图 =================
# 使用 APIView
class TeacherApiView(APIView):
    def get(self, request, tid, format=None):
        print('TeacherView.get - tid: ', tid)
        # params = request.query_params
        # print(params)
        teacher = Teacher.objects.all().filter(tid=tid)
        print(teacher)
        # 这里即使上面返回的只有一个teacher的数据，也要使用 many=True
        # 使用序列化器的 instance 参数，表示此时对数据执行序列化
        serializer = TeacherSerializer(instance=teacher, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def post(self, request,  tid, format=None):
        # 这里post其实是不需要tid参数的，但是由于它和上面的 get 使用了同样的 URL，上面的get带了 tid 参数，并且 URL映射里配置了参数，所以这里
        # 也必须要有一个
        print('TeacherView.post - data: ', request.data)
        data = request.data
        # 使用 data 参数，表示对数据执行反序列化过程
        serializer = TeacherSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# 上面的APIView里面，还是需要写一些重复代码，所以 DRF 封装了下面实现了基本CRUD的类供使用
# 使用 GenericAPI类 和 Mixin类 减少代码
# + GenericAPIView 继承于 APIView，封装了 QuerySet检查、序列化器检查、分页返回 的逻辑，需要我们提供 指定Model的QuerySet 和 对应的序列化类。
# + get, post, put, delete 等方法后面的查询以及序列化/反序列化的过程，交由 mixins 中的 RetrieveModelMixin, ListModelMixin,
#   CreateModelMixin 等工具类实现。
class TeacherGenericView(GenericAPIView, RetrieveModelMixin, ListModelMixin, CreateModelMixin):
    # 下面这段注释会显示在DRF的接口测试页面上；
    # 并且POST方法还会提供一个表单填写框，比较方便。
    """
    使用 GenericAPIView + Mixin工具类 构建视图
    """
    # 设置查询结果集
    queryset = Teacher.objects.all()
    # 设置序列化的类
    serializer_class = TeacherSerializer
    # GenericAPIView 里设置了一个默认的查询字段为 pk，这里需要重写
    lookup_field = 'tid'

    def get(self, request, *args, **kwargs):
        """
        GET 方法对应于两种情况，如果传入了 tid，那就返回指定的教师；如果没有传入，就返回所有老师。
        第1种情况，使用的是 RetrieveModelMixin 引入的 retrieve 方法；
        第2种情况，使用的是 ListModelMixin 引入的 list 方法。
        不过通常会在 RetrieveModelMixin 和 ListModelMixin 中二选一，因为它们都对应于 get 方法。
        """
        tid = kwargs.get('tid')
        if tid == 0:
            # ListModelMixin 引入的方法
            # 如果想自定义一些细节，需要重写 get_serializer 方法——它也是 ListModelMixin.list 内部调用的方法
            return self.list(request, *args, **kwargs)
        else:
            # RetrieveModelMixin 引入的方法
            # 如果想自定义一些细节，需要重写 get_serializer 方法——它是 RetrieveModelMixin.retrieve 内部调用的方法
            return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # 使用的是 CreateModelMixin 引入的方法
        # 如果想自定义一些细节，需要重写 perform_create 方法——它是 CreateModelMixin.create 内部调用的方法
        return self.create(request, *args, **kwargs)


# 上面 GenericAPIView + xxxModelMixin 的方式，已经减少了不少重复代码，但是其实 DRF 还做了更进一步的封装，
# 提供了一套常用的将 Mixin 类与 GenericAPI类已经组合好了的视图，开箱即用
class TeacherCompositeView(ListCreateAPIView):
    # ListCreateAPIView = GenericAPIView + ListModelMixin + CreateModelMixin，并且其中的 get, post 方法已经帮我们实现好了
    """
    使用 ListCreateAPIView 构建视图函数
    """
    # 设置查询结果集
    queryset = Teacher.objects.all()
    # 设置序列化的类
    serializer_class = TeacherSerializer
    # GenericAPIView 里设置了一个默认的查询字段为 pk，这里需要重写
    lookup_field = 'tid'


# 更进一步的，rest_framework.viewsets 中提供了封装好 List、Create、Retrieve、Update、Destroy中多个操作的视图集和类
# 这样 queryset 和 seralizer_class 属性也只需定义一次就好，更加省事。
# ModelViewSet：一次性提供List、Create、Retrieve、Update、Destroy 这5种操作
# ReadOnlyModelViewSet：只提供 List、Retrieve 这2种操作
class TeacherViewSet(ReadOnlyModelViewSet):
    """
    使用 ViewSet 构建视图函数
    """
    # 设置查询结果集
    queryset = Teacher.objects.all()
    # 设置序列化的类
    serializer_class = TeacherSerializer
    # GenericAPIView 里设置了一个默认的查询字段为 pk，这里需要重写
    lookup_field = 'tid'
