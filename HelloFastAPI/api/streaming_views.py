"""
流式响应练习
"""
from typing import Union
from pydantic import BaseModel
from fastapi import APIRouter, Path, Query, Body, Request, status
from fastapi.responses import Response, JSONResponse, StreamingResponse, HTMLResponse
import asyncio

streaming_router = APIRouter(
    prefix='/streaming',
    tags=['API-Streaming']
)


@streaming_router.get("/", response_class=HTMLResponse)
async def hello_streaming():
    """ Hello for Streaming View """
    return "<h1>Hello for Streaming Response</h1>\n"


async def generate_data():
    for i in range(5):
        yield f"streaming content [{i}]...\n"
        await asyncio.sleep(1)

@streaming_router.get("/contents", response_class=StreamingResponse)
async def stream_data():
    """ Streaming Contents """
    return StreamingResponse(generate_data(), media_type="text/plain")
