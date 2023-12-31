"""
自定义 DRF 的权限+鉴权类
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS

# 需要继承 BasePermission 类
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

