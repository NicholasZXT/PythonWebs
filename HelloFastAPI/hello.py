from typing import Union
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse, PlainTextResponse, HTMLResponse

app = FastAPI()


'''
返回响应：https://fastapi.tiangolo.com/zh/advanced/response-directly/
FastAPI 默认会使用 jsonable_encoder 将这些类型的返回值转换成 JSON 格式，
然后 FastAPI 会在后台将这些兼容 JSON 的数据（比如字典）放到一个 JSONResponse 中，该 JSONResponse 会用来发送响应给客户端
'''
@app.get("/hello_root_v1")
def read_root_v1():
    return {"Hello": "World"}

@app.get("/hello_root_v2")
def read_root_v2():
    # 完整写法
    data = {"Hello": "World"}
    json_compatible_item_data = jsonable_encoder(data)
    return JSONResponse(content=json_compatible_item_data)

@app.get("/hello_v1")
def hello_fastapi_v1():
    # 字符串也会被转成JSON
    return "<h1>Hello FastAPI !</h1>"

@app.get("/hello_v2", response_class=PlainTextResponse)
def hello_fastapi_v2():
    html = "<h1>Hello FastAPI !</h1>"
    # return Response(content=html, media_type="text/plain")
    return PlainTextResponse(content=html)

@app.get("/hello_v3", response_class=HTMLResponse)
def hello_fastapi_v3():
    html = "<h1>Hello FastAPI !</h1>"
    return HTMLResponse(content=html)

# URL查询参数 q
@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

# 定义请求体
class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_id": item_id, "item_name": item.name, "item_price": item.price}
