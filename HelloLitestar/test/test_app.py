from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient, AsyncTestClient

# 从 main 文件里导入 app
from main import app
app.debug = True


def test_health_check_sync():
    """
    同步客户端测试
    :return:
    """
    hello_str = "Hello Litestar !"
    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == hello_str


async def test_health_check_async():
    """
    异步客户端测试
    :return:
    """
    hello_str = "Hello Litestar !"
    async with AsyncTestClient(app=app) as client:
        response = await client.get("/")
        assert response.status_code == HTTP_200_OK
        assert response.text == hello_str
