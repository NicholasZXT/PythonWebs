
Python里认证+授权相关的package有如下几个：
+ `passlib`: 专门用于对密码进行哈希散列的库
+ `itsdangerous`: 专门用于对数据进行签名，保证数据在不可信环境下的传输
+ `pyjwt`: 专门用于JWT的编码/解码
+ `python-jose`: The JavaScript Object Signing and Encryption (JOSE) 的Python版，
  提供了JSON Web Signature (JWS), JSON Web Token (JWT), JSON Web Key (JWK), JSON Web Encryption (JWE) 的签名方案.  
+ `authlib`: 用于构建 OAuth 和 OpenID Connect 服务的Python库，包含了用户认证+授权相关的全套内容.

------
# PassLib

官网地址 [PassLib](https://passlib.readthedocs.io/en/stable/#welcome).

根据官方文档 [Library Overview](https://passlib.readthedocs.io/en/stable/narr/overview.html) 的说明，passlib的内容主要分为4部分： 
+ Password Hashes: 用于对密码进行哈希散列的类，基本都在 `passlib.hash` 子模块里.
+ Password Context: 管理密码hash算法的上下文环境，由 `passlib.context` 子模块提供，里面只有一个 `CryptContext` 类
+ Two-Factor Authentication: 用于双重身份验证，提供了TOTP方案（基于时间的一次性密码(Time-based One-time Password)），由 `passlib.totp` 子模块提供
+ Application Helpers: 一些辅助类工具，比如 `passlib.apps`, `passlib.hosts`, `passlib.apache`, `passlib.ext.django` 等

这里只介绍前两个模块的使用。

## passlib.hash 模块
官方文档 [PasswordHash Tutorial](https://passlib.readthedocs.io/en/stable/narr/hash-tutorial.html#hash-tutorial).

`passlib.hash` 模块提供了许多哈希算法，所有哈希算法继承于同一个抽象类 `passlib.ifc.PasswordHash`，该类提供了3类功能：
+ 创建&验证密码的哈希值
+ 检查hasher的配置，并进行自定义
+ 其他辅助方法

使用起来比较简单：
```python
# 导入指定的hasher
from passlib.hash import pbkdf2_sha256

# 计算散列值
hash = pbkdf2_sha256.hash("password")
print(hash)
# '$pbkdf2-sha256$29000$9t7be09prfXee2/NOUeotQ$Y.RDnnq8vsezSZSKy1QNy6xhKPdoBIwc.0XDdRm9sJ8'

# 验证散列值
pbkdf2_sha256.verify("password", hash)
# True
pbkdf2_sha256.verify("joshua", hash)
# False

# 检查是否是此哈希算法得到的值
pbkdf2_sha256.identify(hash)
# True
```

## passlib.context 模块
官方文档 [CryptContext Tutorial](https://passlib.readthedocs.io/en/stable/narr/context-tutorial.html).

只有一个类 `CryptContext`，它用于同时管理多个哈希散列算法，提供统一的入口，使用起来也比较简单：
```python
from passlib.context import CryptContext
# 它的初始化参数是 passlib.hash 里的散列算法名称，本质上它内部会维护多个传入的哈希算法对象
myctx = CryptContext(schemes=["sha256_crypt", "md5_crypt", "des_crypt"])
# 指定默认使用的哈希算法，默认下会使用第一个配置的哈希算法
myctx = CryptContext(schemes=["sha256_crypt", "md5_crypt", "des_crypt"], default="des_crypt")

# 使用时和原本的哈希算法接口一致
hash1 = myctx.hash("joshua")
print(hash)
# '$5$rounds=80000$HFEGd1wnFknpibRl$VZqjyYcTenv7CtOf986hxuE0pRaGXnuLXyfb7m9xL69'
myctx.verify("gtnw", hash1)
# True
myctx.identify(hash)
# "sha256_crypt"
```
有些哈希算法有自定义的配置参数，有两种方式进行配置：
```python
from passlib.context import CryptContext
# 1: 初始化时配置
myctx = CryptContext(
  schemes=["sha256_crypt", "ldap_salted_md5"], 
  sha256_crypt__default_rounds=91234, 
  ldap_salted_md5__salt_size=16
)

# 2. 后续 通过 update() 方法更新
myctx = CryptContext(schemes=["sha256_crypt", "ldap_salted_md5"])
myctx.update(sha256_crypt__default_rounds=91234, ldap_salted_md5__salt_size=16)

# 可以通过如下方法导出/导入配置
cfg_dict = myctx.to_dict()
cfg_str = myctx.to_string()

myctx2 = CryptContext.from_string(cfg_str)
```

------
# ItsDangerous

官网地址 [ItsDangerous](https://itsdangerous.palletsprojects.com/en/2.2.x/), 此package属于 Pallet 项目（Flask项目同属）。

itsdangerous库用于生成可靠签名和验证签名，提供了两个层次的抽象：
+ `Signer`, 用于对指定字符串生成`bytes`的哈希摘要，一般不会直接使用这个层次的对象
+ `Serializer`, 对`Signer`进行了一层封装，可以对一般性的数据进行序列化生成签名，**一般使用这个层次的接口即可**。

提供的主要API如下：
+ `Signer`, 最基本的摘要类
+ `TimestampSigner`, 带时间戳的摘要类
+ `Serializer`, 最基本的序列化类
+ `TimedSerializer`, 带时间戳的序列化类
+ URL相关的两个类：
  + `URLSafeSerializer`
  + `URLSafeTimedSerializer`
+ 常用的验证异常：
  + `BadData`
  + `BadSignature`
  + `BadTimeSignature`
  + `SignatureExpired`

注意，2.0.1 及其之前的版本里还有`JSONWebSignatureSerializer`和`TimedJSONWebSignatureSerializer`，但是后面被取消了，
官方文档推荐使用 `authlib` 之类的专用JWT package 实现类似功能。


------
# PyJWT

官网地址 [PyJWT](https://pyjwt.readthedocs.io/en/stable/).


------
# python-jose

官网地址 [python-jose](https://python-jose.readthedocs.io/en/latest/).


------
# Authlib

官网地址 [Authlib: Python Authentication](https://docs.authlib.org/en/latest/).