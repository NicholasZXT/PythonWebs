from typing import Annotated, List
from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, Request
from fastapi.responses import JSONResponse

file_router = APIRouter(
    prefix='/file',
    tags=['FileUpload-App']
)


# 方式一：使用 UploadFile —— 比较推荐
@file_router.post(
    path='/upload',
    summary='文件上传-V1',
    response_class=JSONResponse
)
async def upload(file: UploadFile):
    filename = file.filename
    print(f"filename: {filename}")
    print(f"file.content_type: {file.content_type}")
    content = await file.read()
    print(f"len(content): {len(content)}")
    with open("test-uploadFile.docx", 'wb') as f:
        f.write(content)
    return {"file-bytes-len": len(content)}


# 方式二：使用 File
@file_router.post(
    path='/upload/v2',
    summary='文件上传-V2',
    response_class=JSONResponse
)
async def upload_v2(file: Annotated[bytes, File()], request: Request):
    print(f"len(file): {len(file)}")
    with open("test-File.docx", 'wb') as f:
        f.write(file)
    # body = await request.body()
    return {"file-bytes-len": len(file)}
