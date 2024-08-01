# -*- coding: utf-8 -*-
# --------------------------------------------------------
# 此文件是 Flask-Principal v-0.4.0 的源码，用于研究其中的逻辑
# --------------------------------------------------------
"""
flask_principal
~~~~~~~~~~~~~~~
Identity management for Flask.
:copyright: (c) 2012 by Ali Afshar.
:license: MIT, see LICENSE for more details.
"""

from __future__ import with_statement
__version__ = '0.4.0'
import sys
from functools import partial, wraps
from collections import deque
from collections import namedtuple
from flask import g, session, current_app, abort, request
from flask.signals import Namespace
PY3 = sys.version_info[0] == 3

# ------------------------------------------------------------------------------------
"""
写在最前面的使用总结，Flask-Principal中，开发者需要关心的几个装饰器或者方法如下：
1. 信号量 identity_changed.send() 方法：此方法用于通知Principal，用户身份有变更。
   **一般会在登录视图函数里调用此方法**
2. @Permission.require : 此装饰器用于保护需要校验权限的视图函数
3. Permission.can() : 此方法用于开发者 在视图函数中 进行权限校验时使用，和上面的装饰器 可以二选一，方便开发者使用
4. 信号量 @identity_loaded.connect : 此装饰器用于注册一个回调函数，在用户身份Identity **加载之后** 的执行一些自定义操作。
   **一般会在这里实现 根据用户ID获取用户所持有权限（Needs）的逻辑，然后存入 Identity.provides 里面**。
5. @Principal.identity_loader : 此装饰器用于注册 **每次请求前** 获取用户身份的回调函数（无参）。
   **从源码逻辑来看，如果初始化Principal对象时use_sessions=False，此时必须要设置一个获取用户身份的回调函数，否则就一直是匿名用户状态**
6. @Principal.identity_saver : 此装饰器用于持久化已经获取的用户身份信息，供下次请求使用

使用感想：
Flask-Principal是一个很松散（loose）的框架，**扩展本身只是提供了一套RBAC的权限校验逻辑**，对于用户身份认证（Authentication providers）
和用户信息来源（User information providers）这两者做了解耦，并且本身也没有依赖任何具体的实现。
1. 用户身份认证（Authentication）可以交由 Flask-Login、Flask-HttpAuth、Flask-JWT-Extended 这些 providers 实现；
2. 用户的信息（包含相关的角色、权限信息）的 provider 可以是MySQL，也可以是内存中的数据结构，甚至是Redis
3. 这样的设计其实还挺巧妙的，对于开发者来说，有比较大的自由发挥空间
4. 但是弊端就是，用户信息这个部分，比如 Need、Permission、Identity对象的管理就需要开发者自己来实现，不像Django那样，
   在django.contrib.auth.models里直接帮开发者定义好了User（对应于Identity），Permission（对应于Need），Group（对应于Permission）
   这3个数据模型。
   **实际上，这部分的工作，正是作者的另外一个扩展Flask-Security要解决的问题。**

PS. 这里研究完Flask-Principal的源码之后，再去看Flask-Principal官方文档以及里面的几个示例代码后，感觉就比较容易明白那些示例代码的作用了。
"""

# ------------------------------------------------------------------------------------
"""
在Flask-Principal中，下面的 两个信号量对象 和 Principal对象 一起工作，它们并不直接和 Need, Permission, IdentityContext 交互，
而是只负责监听 Identity 的读取/变更，并将其存入Flask的全局对象 g 中. 
"""

# Flask-Principal使用了Flask的信号量来实现通信解耦，记录用户身份的变化，这个信号量底层是由 Blinker 实现的
signals = Namespace()

# 用于记录/通知用户身份变更的信号量
# Principal会在 init_app() 方法里使用 .connect() 订阅此信号量，注册回调函数 ._on_identity_changed()
# 而此信号量的 .send() 方法需要开发者来调用，因为用户身份变更的逻辑要开发者来实现，一般有下面两种情况：
# 1. 用户首次登录会话时，验证过request里的username+password，确认用户身份后，创建一个该用户对应的 Identity 对象，然后调用此信号量的 send 方法
# 2. 当前会话的后续请求过程中，每次请求从session里获取用户身份信息，如果有变更，则调用此信号量的 send 方法
# 调用 .send() 方法时传入的参数只能有2个：第1个sender参数必须是当前的 Flask 对象，第2个参数必须是 Identity 对象——也就是获取的用户身份
identity_changed = signals.signal('identity-changed', doc="""
Signal sent when the identity for a request has been changed.

Actual name: ``identity-changed``

Authentication providers should send this signal when authentication has been
successfully performed. Flask-Principal connects to this signal and
causes the identity to be saved in the session.

For example::

    from flaskext.principal import Identity, identity_changed

    def login_view(req):
        username = req.form.get('username')
        # check the credentials
        identity_changed.send(app, identity=Identity(username))
""")

# 用于记录用户身份加载的信号量
# Principal只会在 Principal.set_identity() 方法里调用该信号量的 send() 方法，**不会调用该信号量的 connect() 方法注册任何操作**
# 所以这个信号量不是给Principal内部使用的，而是 **提供给开发者使用的**，方便开发者在得知用户身份加载之后，自定义一些操作。
# 如果开发者要自定义用户身份加载时的操作时，要使用此信号量的 @identity_loaded.connect 装饰器注册一个接收此信号量之后的回调函数
# 常见的一个操作是，在回调函数里对用户所持有的角色/权限进行查询加载（如下面文档的例子里那样）
# 使用 connect 装饰器方法注册的 回调函数，必须接受两个参数： 第1个位置参数sender是Flask对象，一般不用管；第2个参数就是获取的 Identity 对象
identity_loaded = signals.signal('identity-loaded', doc="""
Signal sent when the identity has been initialised for a request.

Actual name: ``identity-loaded``

Identity information providers should connect to this signal to perform two
major activities:

    1. Populate the identity object with the necessary authorization provisions.
    2. Load any additional user information.

For example::

    from flaskext.principal import identity_loaded, RoleNeed, UserNeed

    @identity_loaded.connect
    def on_identity_loaded(sender, identity):
        # Get the user information from the db
        user = db.get(identity.name)
        # Update the roles that a user can provide
        for role in user.roles:
            identity.provides.add(RoleNeed(role.name))
        # Save the user somewhere so we only look it up once
        identity.user = user
""")

# -------------------------------------------------------------------------------
"""
Need, Identity, Permission 和 IdentityContext 这4个对象在Flask-Principal中是一起工作的，负责对用户具体操作权限的检查。
除了Identity，其他3个对象和 Principal 对象并不交互。
一般使用逻辑为：
1. 使用一系列的表示权限的 Need 对象，来实例化一个 Permission 对象，存入 Permission.needs 属性里
  1.1 这个Permission对象就表示了一个待校验的权限集合，后续的校验都是从Permission对象发起
  1.2 各种类型的Permission对象之间，可以很容易的通过类似于set的交、并、补、差运算，得到新的Permission对象
2. 由Permission对象发起权限校验，也就是使用 Permission.require() 来装饰视图函数，返回的 IdentityContext 会对视图函数进行封装
  2.1 Permission.require()返回 IdentityContext 时，将自己也传递给 IdentityContext
  2.2 IdentityContext 会通过 g.identity 获取当前请求的用户身份Identity对象，Identity.provides里也是一系列的 Need 对象
  2.3 因此 IdentityContext 同时持有了 Permission 和 用户身份Identity
3. IdentityContext 在每次执行视图函数前，会调用 self.can() 方法进行权限校验
  3.1 self.can() 方法里 return self.identity.can(self.permission)
  3.2 identity.can(permission) 方法里 return permission.allows(self)
  3.3 permission.allow(identity) 方法里 会对 permission.needs 和 identity.provides 进行权限校验
  我个人觉得 3.1 + 3.2 这两步有些啰嗦，直接在 IdentityContext.can() 方法中使用 self.permission.allow(self.identity) 似乎就可以了。 
"""

# Need 是某种操作权限的描述，它是最细粒度的权限对象，作者使用了元组来描述操作权限。
# 一般有两种操作权限：
# 1. 一种是像下面Need一样，只需要记录两个信息的权限对象，表示Identity需要属于该角色（类似用户组）才能通过权限校验。
#    method记录的是角色的分组类型，比如下面的 UserNeed, RoleNeed等，value就是该类型中具体某个角色 —— 不过我觉得method这个命名不太恰当
# 2. 另一种是下面 ItemNeed 一样，需要3个元素的元组描述，表示object级别的操作权限，也就是Identity对某个表中某行记录进行CRUD操作的权限
Need = namedtuple('Need', ['method', 'value'])
"""A required need

This is just a named tuple, and practically any tuple will do.

The ``method`` attribute can be used to look up element 0, and the ``value``
attribute can be used to look up element 1.
"""

UserNeed = partial(Need, 'id')
UserNeed.__doc__ = """A need with the method preset to `"id"`."""

RoleNeed = partial(Need, 'role')
RoleNeed.__doc__ = """A need with the method preset to `"role"`."""

TypeNeed = partial(Need, 'type')
TypeNeed.__doc__ = """A need with the method preset to `"type"`."""

ActionNeed = partial(Need, 'action')
TypeNeed.__doc__ = """A need with the method preset to `"action"`."""


ItemNeed = namedtuple('ItemNeed', ['method', 'value', 'type'])
"""A required item need

An item need is just a named tuple, and practically any tuple will do. In
addition to other Needs, there is a type, for example this could be specified
as::

    ItemNeed('update', 27, 'posts')
    ('update', 27, 'posts') # or like this

And that might describe the permission to update a particular blog post. In
reality, the developer is free to choose whatever convention the permissions
are.
"""


class PermissionDenied(RuntimeError):
    """Permission denied to the resource"""

# Identity 对象是对用户身份和权限的抽象，一般在用户登录的时候创建对应当前用户身份的Identity对象，并在后续会话的请求中从session中加载
# id 字段用于存放用户身份的唯一标识，auth_type 用于验证用户身份的鉴权类型，不过在整个 Principal 权限校验过程中并不会使用这个值
# provides 字段记录的是一系列的 Need set，表示该用户持有的权限
class Identity(object):
    """Represent the user's identity.

    :param id: The user id
    :param auth_type: The authentication type used to confirm the user's
                      identity.

    The identity is used to represent the user's identity in the system. This
    object is created on login, or on the start of the request as loaded from
    the user's session.

    Once loaded it is sent using the `identity-loaded` signal, and should be
    populated with additional required information.

    Needs that are provided by this identity should be added to the `provides`
    set after loading.
    """
    def __init__(self, id, auth_type=None):
        self.id = id
        self.auth_type = auth_type
        self.provides = set()

    # 个人感觉下面这个方法有点多余了，不过可能是留给开发者在视图函数中自己进行权限检查使用的？？
    def can(self, permission):
        """Whether the identity has access to the permission.

        :param permission: The permission to test provision for.
        """
        return permission.allows(self)

    def __repr__(self):
        return '<{0} id="{1}" auth_type="{2}" provides={3}>'.format(
            self.__class__.__name__, self.id, self.auth_type, self.provides
        )


class AnonymousIdentity(Identity):
    """An anonymous identity"""

    def __init__(self):
        Identity.__init__(self, None)

# 权限校验的上下文对象，它和表示某类权限的 Permission 对象绑定，一般由对应的 Permission.require装饰器 返回，只负责对当前 Permission 进行校验
# 返回时，它会持有当前的 Permission 对象，然后从Flask g 全局对象中获取当前请求的用户对象 Identity
# 权限校验时，检查 Identity.provides 和 Permission.needs 是否有交集，有则表示有权限
class IdentityContext(object):
    """The context of an identity for a permission.

    .. note:: The principal is usually created by the flaskext.Permission.require method
              call for normal use-cases.

    The principal behaves as either a context manager or a decorator. The
    permission is checked for provision in the identity, and if available the
    flow is continued (context manager) or the function is executed (decorator).
    """
    # IdentityContext一般由 Permission.require() 方法创建，创建的时候，Permission对象会将自己传入构造方法里的 permission ------ KEY
    def __init__(self, permission, http_exception=None):
        self.permission = permission  # 该IdentityContext所对应的Permission对象
        self.http_exception = http_exception  # 权限校验失败时的 http 错误码，比如 404
        """ The permission of this principal """

    @property
    def identity(self):
        """ The identity of this principal """
        # 这里通过Flask全局对象 g 获取 用户身份 Identity 对象，它有两个地方可以存入：
        # 1. 由 Principal 对象在 ._on_before_request() 方法中存入的
        # 2. 由 Principal 对象在 ._on_identity_changed() 方法中存入，此方法是 Principal在订阅信号量identity_changed时设置的回调函数
        return g.identity

    def can(self):
        """ Whether the identity has access to the permission """
        # print(f"IdentityContext.can(): self.identity - {self.identity}...")
        current_app.logger.debug(f"IdentityContext.can(): self.identity - {self.identity}...")
        return self.identity.can(self.permission)
        # Identity.can(permission) 里调用的是 return permission.allows(self)，所以我感觉 Identity.can() 方法有点多余
        # 下面这个逻辑似乎更直接一点？
        # return self.permission.allow(self.identity)

    def __call__(self, f):
        @wraps(f)
        def _decorated(*args, **kw):
            with self:
                rv = f(*args, **kw)
            return rv
        return _decorated

    def __enter__(self):
        # check the permission here
        if not self.can():
            if self.http_exception:
                abort(self.http_exception, self.permission)
            raise PermissionDenied(self.permission)

    def __exit__(self, *args):
        return False


# 它是权限校验的主要入口对象，持有 Need 构成的权限set，一般使用 Permission.require 装饰需要保护的视图函数
# .require()方法 会返回一个 IdentityContext 对象，对视图函数进行包装，在每次请求前执行权限校验操作
class Permission(object):
    """Represents needs, any of which must be present to access a resource
    :param needs: The needs for this permission
    """
    def __init__(self, *needs):
        """A set of needs, any of which must be present in an identity to have
        access.
        """
        # 记录当前Permission对象所包含的权限Need集合
        self.needs = set(needs)
        self.excludes = set()  # 这个是留给它的子类 Denial 的属性

    def _bool(self):
        return bool(self.can())

    def __nonzero__(self):
        """Equivalent to ``self.can()``.
        """
        return self._bool()

    def __bool__(self):
        """Equivalent to ``self.can()``.
        """
        return self._bool()

    def __and__(self, other):
        """Does the same thing as ``self.union(other)``
        """
        return self.union(other)

    def __or__(self, other):
        """Does the same thing as ``self.difference(other)``
        """
        return self.difference(other)

    def __contains__(self, other):
        """Does the same thing as ``other.issubset(self)``.
        """
        return other.issubset(self)

    def __repr__(self):
        return '<{0} needs={1} excludes={2}>'.format(
            self.__class__.__name__, self.needs, self.excludes
        )

    # 用于装饰视图函数的装饰器方法  ------------------------------------------------------- KEY
    def require(self, http_exception=None):
        """Create a principal for this permission.

        The principal may be used as a context manager, or a decroator.

        If ``http_exception`` is passed then ``abort()`` will be called
        with the HTTP exception code. Otherwise a ``PermissionDenied``
        exception will be raised if the identity does not meet the
        requirements.

        :param http_exception: the HTTP exception code (403, 401 etc)
        """
        # 这里返回 IdentityContext 对象时，把当前 Permission 对象自己（self）也传进去了
        # IdentityContext 对象始终是和当前的 Permission 对象绑定的，只负责校验当前 Permission 对应的权限
        return IdentityContext(self, http_exception)

    def test(self, http_exception=None):
        """
        Checks if permission available and raises relevant exception
        if not. This is useful if you just want to check permission
        without wrapping everything in a require() block.

        This is equivalent to::

            with permission.require():
                pass
        """

        with self.require(http_exception):
            pass

    def reverse(self):
        """
        Returns reverse of current state (needs->excludes, excludes->needs)
        """

        p = Permission()
        p.needs.update(self.excludes)
        p.excludes.update(self.needs)
        return p

    def union(self, other):
        """Create a new permission with the requirements of the union of this
        and other.

        :param other: The other permission
        """
        p = Permission(*self.needs.union(other.needs))
        p.excludes.update(self.excludes.union(other.excludes))
        return p

    def difference(self, other):
        """Create a new permission consisting of requirements in this
        permission and not in the other.
        """

        p = Permission(*self.needs.difference(other.needs))
        p.excludes.update(self.excludes.difference(other.excludes))
        return p

    def issubset(self, other):
        """Whether this permission needs are a subset of another

        :param other: The other permission
        """
        return (
            self.needs.issubset(other.needs) and
            self.excludes.issubset(other.excludes)
        )

    # 下面这个方法进行实际的权限校验 ------------------------------------------------------- KEY
    def allows(self, identity):
        """Whether the identity can access this permission.

        :param identity: The identity
        """
        if self.needs and not self.needs.intersection(identity.provides):
            return False

        if self.excludes and self.excludes.intersection(identity.provides):
            return False

        return True

    # 这个方法是留给开发者在视图函数中进行校验时使用的
    def can(self):
        """Whether the required context for this permission has access

        This creates an identity context and tests whether it can access this
        permission
        """
        return self.require().can()


class Denial(Permission):
    """
    Shortcut class for passing excluded needs.
    """

    def __init__(self, *excludes):
        self.excludes = set(excludes)
        self.needs = set()


def session_identity_loader():
    if 'identity.id' in session and 'identity.auth_type' in session:
        identity = Identity(session['identity.id'],
                            session['identity.auth_type'])
        return identity


def session_identity_saver(identity):
    session['identity.id'] = identity.id
    session['identity.auth_type'] = identity.auth_type
    session.modified = True

# Principal 对象主要和一开始定义的两个信号量 identity_changed, identity_loaded 交互，负责用户身份Identity的加载/变更记录
class Principal(object):
    """Principal extension

    :param app: The flask application to extend
    :param use_sessions: Whether to use sessions to extract and store
                         identification.
    :param skip_static: Whether to ignore static endpoints.
    """
    def __init__(self, app=None, use_sessions=True, skip_static=False):
        self.identity_loaders = deque()
        self.identity_savers = deque()
        # XXX This will probably vanish for a better API
        self.use_sessions = use_sessions
        self.skip_static = skip_static

        if app is not None:
            self.init_app(app)

    def _init_app(self, app):
        from warnings import warn
        warn(DeprecationWarning(
            '_init_app is deprecated, use the new init_app '
            'method instead.'), stacklevel=1
        )
        self.init_app(app)

    def init_app(self, app):
        if hasattr(app, 'static_url_path'):
            self._static_path = app.static_url_path
        else:
            self._static_path = app.static_path

        # 这里在每个请求前面都进行了 用户Identity 的获取 ---------------------------------------------- KEY
        app.before_request(self._on_before_request)

        # 订阅 identity_change信号量，注册的回调函数是 ._on_identity_changed，里面会向Flask全局对象g中存入获取到的用户身份Identity
        # 并向 identity_loaded信号量 发送消息，通知用户自定义的函数
        # 一般来说，会在登录的视图函数里调用这个信号量的 .send() 方法，告知Flask-Principal用户身份已更新 --------------------- KEY
        # 此信号量的 sender （第2个参数）指定为 app，也就是当前的 Flask 对象
        identity_changed.connect(self._on_identity_changed, app)
        # ----------------------------------------------------------------------------------------------
        # 有个问题是：这里的回调函数即使更新了 g.identity，每次请求也会被上面的 self._on_before_request() 再次更新，
        # 因此 self.identity_loaders 里必须要有一个加载用户身份的回调函数，否则就会一直是 g.identity = AnonymousIdentity 的状态
        # ----------------------------------------------------------------------------------------------

        # print(f"Principal.init_app: use_sessions is {self.use_sessions}...")
        current_app.logger.debug(f"Principal.init_app -> final action: use_sessions is {self.use_sessions}...")
        if self.use_sessions:
            self.identity_loader(session_identity_loader)
            self.identity_saver(session_identity_saver)

    def set_identity(self, identity):
        """Set the current identity.
        :param identity: The identity to set
        """
        # print(f"Principal.set_identity: Flask g.identity is set to {identity}...")
        current_app.logger.debug(f"Principal.set_identity: Flask g.identity is set to {identity}...")
        self._set_thread_identity(identity)
        for saver in self.identity_savers:
            saver(identity)

    # 开发者可以使用这个装饰器来注册 一个或者多个 执行 用户身份获取 的 无参函数
    # 在每个请求前，Principal 依次调用注册的 loader 来获取一个 用户身份Identity，否则就都是 AnonymousIdentity()
    def identity_loader(self, f):
        """Decorator to define a function as an identity loader.

        An identity loader function is called before request to find any
        provided identities. The first found identity is used to load from.

        For example::

            app = Flask(__name__)

            principals = Principal(app)

            @principals.identity_loader
            def load_identity_from_weird_usecase():
                return Identity('ali')
        """
        self.identity_loaders.appendleft(f)
        return f

    def identity_saver(self, f):
        """Decorator to define a function as an identity saver.

        An identity loader saver is called when the identity is set to persist
        it for the next request.

        For example::

            app = Flask(__name__)

            principals = Principal(app)

            @principals.identity_saver
            def save_identity_to_weird_usecase(identity):
                my_special_cookie['identity'] = identity
        """
        self.identity_savers.appendleft(f)
        return f

    def _set_thread_identity(self, identity):
        # 在这里向Flask全局对象 g 中存入的获取到的用户身份Identity
        g.identity = identity
        # 这个向信号量发送信息的方法里，第一个参数是发送者——这是Flask建议的固定写法，第二个参数是要发送的内容——这里是表示用户身份的 Identity 对象
        # 这里向信号量发送消息，主要是为了通知并触发用户自定义的操作，Principal本身不会通过 .connect() 订阅这个信号量 ------- KEY
        identity_loaded.send(current_app._get_current_object(), identity=identity)

    def _on_identity_changed(self, app, identity):
        if self._is_static_route():
            return
        # print(f"Principal._on_identity_changed: Identity changed to {identity}...")
        current_app.logger.debug(f"Principal._on_identity_changed: Identity changed to {identity}...")
        self.set_identity(identity)

    def _on_before_request(self):
        if self._is_static_route():
            return
        # 这里在每次请求调用视图函数之前都会将 g.identity 设置为 AnonymousIdentity
        g.identity = AnonymousIdentity()
        # print(f"Principal._on_before_request: Identity reset to AnonymousIdentity...")
        current_app.logger.debug(f"Principal._on_before_request: Identity reset to AnonymousIdentity...")
        # current_app.logger.debug(f"Principal._on_before_request: session: {session}")
        # 依次遍历 self.identity_loaders 里由 Principal.identity_loader 装饰器函数注册的 用户加载回调方法
        # ----------------------------------------------------------------------------------------------
        # 这里的一个问题是：如果没有设置任何 identity_loader 回调函数，也就是 self.identity_loaders 为空
        # 那么下面就不会再次设置 g.identity，会导致一直处于 AnonymousIdentity 的状态。
        # ----------------------------------------------------------------------------------------------
        for loader in self.identity_loaders:
            current_app.logger.debug(f"Principal._on_before_request -> execute loader: {loader}...")
            identity = loader()
            current_app.logger.debug(f"Principal._on_before_request -> loader get identity: {identity}...")
            if identity is not None:
                self.set_identity(identity)
                return

    def _is_static_route(self):
        return (
            self.skip_static and
            request.path.startswith(self._static_path)
        )
