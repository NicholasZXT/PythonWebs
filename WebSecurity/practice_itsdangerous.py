"""
研究itsdangerous包的使用.
"""
from itsdangerous import Signer, Serializer, TimestampSigner, TimedSerializer, URLSafeSerializer, URLSafeTimedSerializer
from itsdangerous import BadData, BadSignature, BadTimeSignature, SignatureExpired

if __name__ == '__main__':
    SECRET_KEY = 'secret-key'  # 加密的KEY，必须是随机的，以保证安全
    salt = "some-salt"         # 加密的盐，用于区分不同上下文环境的，比如注册，激活等场景，可以不设置
    value = "my string"
    # 初始化摘要对象，默认分隔符为 .
    # signer = Signer(secret_key=SECRET_KEY, salt=salt, sep='.')
    signer = Signer(secret_key=SECRET_KEY, salt=salt)
    # sign 方法生成的bytes摘要为：原始字符串.摘要字符串
    s1 = signer.sign(value)
    # 生成的摘要由 . 分隔，放在后面
    # b'my string.jYl76vcNq012USg6gtWnzYe5h0k'
    print(s1)
    # 解析摘要
    s1_rev = signer.unsign(s1)
    print(s1_rev)
    # 如果传入有修改的字符串，则会抛出 BadSignature 异常
    try:
        signer.unsign(b'my string-add.wh6tMHxLgJqB6oY1uT73iMlyrOA')
    except BadSignature as e:
        print("failed to unsign data...")
        print(e)
    # 验证 某个字符串是否为 sign 生成的合法摘要
    signer.validate(s1)
    # 也可以单独生成摘要
    s11 = signer.get_signature(value)
    print(s11)
    # 验证 字符串 和 摘要 是否匹配
    signer.verify_signature(value, s11)

    # 带时间戳的摘要，注意，时间戳设置并不是放在初始化里的
    signer_time = TimestampSigner(secret_key=SECRET_KEY, salt=salt)
    # 获取当前时间戳
    signer_time.get_timestamp()
    signer_time.timestamp_to_datetime(signer_time.get_timestamp())
    # 进行签名，签名中会包含时间戳信息
    s1 = signer_time.sign(value)
    print(s1)
    try:
        # 过期时间的大小设置是由 unsign 方法里 max_age 参数设置（单位似乎是毫秒） --------------- KEY
        s1_rev = signer_time.unsign(signed_value=s1, max_age=500)
        print(s1_rev)
    except SignatureExpired as e:
        print("time expired ...")
        print(e)

    # 序列化摘要
    data = {'data': 'my data', 'timestamp': 'sometime'}
    serializer = Serializer(secret_key=SECRET_KEY, salt=salt)
    # dumps 是序列化+签名为字符，dump 是写入文件
    s2 = serializer.dumps(data)
    print(s2)
    # 但是序列化的字符串里是含有明文表示
    # {"data": "my data", "timestamp": "sometime"}.kWyWgZhlMwXfPTEt86fzKd9silo
    s2_rev = serializer.loads(s2)
    print(s2_rev)
    # 带时间戳的序列化摘要
    serializer_time = TimedSerializer(secret_key=SECRET_KEY, salt=salt)
    s2 = serializer_time.dumps(data)
    print(s2)
    # {"data": "my data", "timestamp": "sometime"}.ZrDm7g.ex3E8KGt0MgYWE64WD_7m2NJZEw
    try:
        s2_rev = serializer_time.loads(s=s2, max_age=100)
        print(s2_rev)
    except BadTimeSignature as e:
        print("time expired ...")
        print(e)

    # Serializer 里序列化有明文，下面的URL序列化就不含明文了
    data = {'data': 'my data', 'timestamp': 'sometime'}
    serializer_url = URLSafeSerializer(secret_key=SECRET_KEY, salt=salt)
    s3 = serializer_url.dumps(data)
    print(s3)
    # eyJkYXRhIjoibXkgZGF0YSIsInRpbWVzdGFtcCI6InNvbWV0aW1lIn0.FSp1K6UbHJ0ItlK_NDKDq4LxgkI
    s3_rev = serializer_url.loads(s3)
    print(s3_rev)
    # 带时间戳的URL序列化摘要
    serializer_url_time = URLSafeTimedSerializer(secret_key=SECRET_KEY, salt=salt)
    s3 = serializer_url_time.dumps(data)
    print(s3)
    # eyJkYXRhIjoibXkgZGF0YSIsInRpbWVzdGFtcCI6InNvbWV0aW1lIn0.ZrDqdw.Oo-h-oyMQWKT-VRfiCoMOzMsewQ
    try:
        s3_rev = serializer_url_time.loads(s=s3, max_age=10)
        print(s3_rev)
    except SignatureExpired as e:
        print("time expired ...")
        print(e)
