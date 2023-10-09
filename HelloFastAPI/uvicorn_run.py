"""
uvicorn 官网文档 https://www.uvicorn.org/#quickstart
使用 uvicorn 在代码中运行 fastAPI
"""
import uvicorn

if __name__ == "__main__":
    port = 8100
    # 第一种方式
    uvicorn.run("hello_main:app", port=port, log_level="info")
    # 第二种方式
    # config = uvicorn.Config("hello_main:app", port=port, log_level="info")
    # server = uvicorn.Server(config)
    # server.run()
