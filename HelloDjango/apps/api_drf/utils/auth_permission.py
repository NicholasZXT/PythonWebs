"""
自定义DRF的 权限控制类 和 基于Token的身份验证类
"""
from django.contrib.auth.models import User
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# 自定义 权限控制类 需要继承 BasePermission 类
# 然后根据需要重写 has_permission(self,request,view) 和 has_object_permission(self,request, view, obj) 方法
class IsOwnerOrReadOnly(BasePermission):
    """
    自定义权限类：只允许对象的创建者才能编辑它
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限被允许用于任何请求，
        # 所以我们始终允许 GET，HEAD 或 OPTIONS 请求。
        if request.method in SAFE_METHODS:
            return True
        # 写入权限只允许给 Draft 的作者
        return obj.author == request.user

# ---------------------------------------------------------------

# 自定义 Token验证类 需要继承 BaseAuthentication 类，然后根据需要重写 .authenticate(self, request) 方法
# + 验证成功，返回一个 (user, auth) 的二元组，然后DRF（不再是Django）会使用这个元组来设置 request.user 和 request.auth 属性
# + 验证失败，返回None
class MyTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        username = request.META.get('X_USERNAME')
        if not username:
            return None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise AuthenticationFailed('No such user')
        # 验证成功，返回一个元祖
        return (user, None)


# 对于 rest_framework_simplejwt ，也可以自定义 Token 格式，只需要继承 TokenObtainPairSerializer 类，然后重写其中的方法
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super(MyTokenObtainPairSerializer, cls).get_token(user)
        # 添加额外信息
        token['username'] = user.username
        return token
