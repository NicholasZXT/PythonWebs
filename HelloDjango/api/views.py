from django.http.response import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Permission, User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, CreateModelMixin, DestroyModelMixin
from rest_framework.generics import GenericAPIView, ListCreateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Student, Teacher, Draft
from .serializers import StudentSerializer, TeacherSerializer, DraftSerializer
from .custom_auth_permission import IsOwnerOrReadOnly

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
#  + ModelViewSet：一次性提供List、Create、Retrieve、Update、Destroy 这5种操作
#  + ReadOnlyModelViewSet：只提供 List、Retrieve 这2种操作
# 但是不太建议使用这个 ViewSet，因为封装的太深了，不好自定义  ----------------- KEY
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


# ================== DRF 用户权限鉴别 ======================

@api_view(http_method_names=['GET'])
def create_draft_user(request, *args, **kwargs):
    # 创建一个专门查看/操作 api_draft 数据表的用户，并设置权限
    User = get_user_model()
    old_user = authenticate(username='draft_user', password='draft2023')
    response_data = {'msg': 'nothing'}
    if old_user is None:
        username = 'draft_user'
        message = f"old user for draft not exits, prepare to create new one with name '{username}' ..."
        print(message)
        response_data['msg'] = message
        draft_user = User.objects.create_user(username=username, password='draft2023', email='nothing@email.com')
        # draft_user.user_permissions.add('api.add_draft', 'api.view_draft', 'api.update_draft', 'api.delete_draft')
        # 这里必须获取 Draft 表的所有权限
        draft_permissions = Permission.objects.filter(content_type=ContentType.objects.get_for_model(Draft)).all()
        draft_user.user_permissions.add(*draft_permissions)
        draft_user.save()
    else:
        message = f"old user for draft exists: {old_user.username}."
        print(message)
        response_data['msg'] = message
    response = JsonResponse(data=response_data)
    return response


class DraftOpenView(GenericAPIView, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Draft.objects.all()
    serializer_class = DraftSerializer
    lookup_field = 'nid'

    # 没有设置用户身份验证的类，也没有设置权限鉴别类

    # 没有登录用户的情况下，下面的3个方法中，只有 GET 能看到数据，POST 和 DELETE 的按钮能看到，但是执行之后，会报未登录错误
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    # 下面自定义了 post 和 delete 内部调用的方法，在里面做了用户身份验证的逻辑，但没有做权限鉴别的控制
    # 这里用户身份验证其实是使用Django本身django.contrib.auth里集成的User用户模型的身份验证：
    #  如果验证通过，Django就会在 request.user 中存放经过认证的用户；
    #  如果认证没有通过，那 request.user 里存放的就是 AnonymousUser 实例
    def perform_create(self, serializer):
        print(f"DraftOpenView - create draft with request.user: {self.request.user}")
        if self.request.user.is_anonymous:
            msg = f"request with anonymous user, not allowed to create."
            print(msg)
            # response = JsonResponse(data={'msg': msg}, status=401)
            raise PermissionDenied(detail=msg)
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        print(f"DraftOpenView - destroy draft with request.user: {self.request.user}")
        if self.request.user.is_anonymous:
            msg = f"request with anonymous user, not allowed to delete."
            print(msg)
            # response = JsonResponse(data={'msg': msg}, status=401)
            raise PermissionDenied(detail=msg)
        instance.delete()


class DraftAuthView(GenericAPIView, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Draft.objects.all()
    serializer_class = DraftSerializer
    lookup_field = 'nid'

    # 设置权限鉴别类，没有权限的用户（包括未登录用户和已登录但无修改权限的用户）只能读，不能改和删
    # 因此GET方法能看到数据，而 POST 和 DELETE 的按钮在未登录的情况下是看不到的
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 其他的权限鉴别类有：
    # AllowAny，允许任何用户访问
    # IsAuthenticated，只允许经过身份验证的用户（所有登录的用户均可以）访问
    # IsAdminUser，只允许管理员访问
    # DjangoModelPermissions，只有在用户经过 身份验证 并分配了相关 数据模型 权限时，才会获得授权访问相关模型
    # DjangoModelPermissionsOrReadOnly，而前者类似，但是未知用户可以查看
    # DjangoObjectPermissions，和 DjangoModelPermissions 类似，但是更加精细，可以设置 数据模型里每个对象（每条数据记录） 的权限

    # 注意，这里的DRF提供的权限鉴别类提供的功能已经是 RBAC(Role-Based Access Control) 粒度的了. --------------------------- KEY

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class DraftOwnerView(GenericAPIView, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Draft.objects.all()
    serializer_class = DraftSerializer
    lookup_field = 'nid'

    # 使用自定义的权限鉴别类，只有用户本身可以编辑，其他人只能读
    permission_classes = [IsOwnerOrReadOnly]

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


# 如果是视图函数，需要使用 permission_classes 装饰器来引入权限类
@api_view(['GET'])
@permission_classes((IsAuthenticated, ))
def draft_permission_view(request, format=None):
    content = {
        'status': 'request was permitted'
    }
    return Response(content)


# ================== DRF 基于Token的身份认证 ======================

class DraftTokenView(ListCreateAPIView):
    queryset = Draft.objects.all()
    serializer_class = DraftSerializer
    lookup_field = 'nid'

    # 设置用户权限鉴别类
    permission_classes = [IsAuthenticatedOrReadOnly]
    # 设置Token认证类
    authentication_classes = [TokenAuthentication]

    # DRF 提供了如下的几个身份认证的类
    # + SessionAuthentication：基于Session的认证，使用Django的默认session后端进行认证
    #   上面的几个视图类里没有配置 authentication_classes 时，就是使用的这个
    # + BasicAuthentication：基于用户名和密码的基本身份认证
    # + TokenAuthentication：就是这里使用的基于Token的身份认证

# 视图函数的话，使用 authentication_classes 装饰器来引入 Token 验证类
@api_view(['GET'])
@authentication_classes((TokenAuthentication,))
@permission_classes((IsAuthenticated,))
def example_view(request, format=None):
    content = {
        'user': request.user,  # `django.contrib.auth.User` 实例。
        'auth': request.auth,  # None
    }
    return JsonResponse(content)

# 但是DRF的 TokenAuthentication 是以一个应用的方式提供的，具体为 rest_framework.authtoken 这个应用。
# 弊端在于，每个用户的Token生成过程不太方便，而且Token是存放在数据库中的（rest_framework.authtoken.models.Token）,不方便设置过期时间和修改
# 因此实际中，推荐使用下面的 JWT 扩展来做基于Token的身份验证

# ------ 使用 rest_framework_simplejwt 提供的JWT验证--------
class DraftJwtView(GenericAPIView, ListModelMixin, CreateModelMixin, DestroyModelMixin):
    queryset = Draft.objects.all()
    serializer_class = DraftSerializer
    lookup_field = 'nid'

    # 设置用户权限鉴别类
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 使用 rest_framework_simplejwt 提供的 Token认证类
    authentication_classes = [JWTAuthentication]
    # 设置完成后，还需要从 rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView 这两个视图函数，
    # 在 url 映射中进行配置，用于获取 access_token 和 refresh_token
    # 当然，也可以自定义上面两个视图函数，只需要继承 rest_framework_simplejwt.views.TokenObtainPairView 类，
    # 并自定义其中的 serializer_class 属性，指向自己写的 Token 序列化类

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)