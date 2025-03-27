import io
import os
from typing import Literal
from minio import Minio, S3Error
from minio.helpers import ObjectWriteResult
from minio.datatypes import Object
from urllib3.response import HTTPResponse
from datetime import timedelta


class MinioClient:
    def __init__(
        self,
        endpoint: str, access_key: str, secret_key: str, bucket_name: str,
        base_path: str = None, secure: bool = False
    ):
        self.client = Minio(endpoint=endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket_name = bucket_name
        # base_path 前面最好不要有 /，否则生成预签名 URL 时，bucket后面会有两个 /，浏览器访问时不会触发下载操作
        self.base_path = base_path

    def wrap_obj_name(self, object_name: str) -> str:
        if self.base_path is None:
            return object_name
        else:
            return f"{self.base_path}/{object_name}"

    def upload_object(
            self, object_name: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> ObjectWriteResult | None:
        """ 直接从字节流中上传对象 """
        data_stream = io.BytesIO(data)
        length = len(data)
        try:
            obj_res = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=self.wrap_obj_name(object_name),
                data=data_stream,
                length=length,
                content_type=content_type
            )
            return obj_res
        except S3Error as e:
            print(f"Failed to upload object {object_name} with S3Error: ", e)
            # pass
        return None

    def upload_file(self, object_name: str, file_path: str) -> ObjectWriteResult | None:
        """ 将本地文件上传到Minio """
        obj_res: ObjectWriteResult | None = None
        try:
            obj_res = self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=self.wrap_obj_name(object_name),
                file_path=file_path
            )
        except S3Error as e:
            print(f"Failed to upload object {object_name} with S3Error: ", e)
        return obj_res

    def get_object(self, object_name: str) -> bytes | None:
        """ 获取对象的字节流 """
        data : bytes | None = None
        # Minio.fget_object 内部也是调用的 Minio.get_object，可以参考该方法源码使用 get_object 方法
        response: HTTPResponse | None = None
        try:
            response: HTTPResponse = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=self.wrap_obj_name(object_name)
            )
            data = response.data
        except S3Error as e:
            print(f"Failed to get object {object_name} with S3Error: ", e)
        finally:
            if response:
                response.close()
                response.release_conn()
        return data

    def download_file(self, object_name: str, file_path: str) -> Object | None:
        """ 直接下载对象，并存入 file_path 指定的文件里 """
        obj: Object | None = None
        try:
            # 返回的是文件信息，也是 Minio.stat_object 的返回值
            obj: Object = self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=self.wrap_obj_name(object_name),
                file_path=file_path
            )
        except S3Error as e:
            print(f"Failed to get object {object_name} with S3Error: ", e)
        return obj

    def delete_object(self, object_name: str):
        try:
            self.client.remove_object(bucket_name=self.bucket_name, object_name=self.wrap_obj_name(object_name))
        except S3Error as e:
            print(f"Failed to delete object {object_name} with S3Error: ", e)
            raise e

    def get_presigned_url(self, object_name: str, expires: int = 7) -> Literal[b""]:
        """ 获取预签名的 URL """
        # 内部调用的 Minio.get_presigned_url 方法，做了一些封装
        url = self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=self.wrap_obj_name(object_name),
            expires=timedelta(days=expires)
        )
        return url


if __name__ == '__main__':
    endpoint = "127.0.0.1:9090"
    access_key = "tGfNmivvHiT4GGnGqxyg"
    secret_key = "1mkR1XFbsZO4imWJWoSWL4bt4bnHAaaywdHctH6P"
    bucket_name = "test"
    base_path = "attachments"  # base_path 不需要以 / 开头
    minio_client = MinioClient(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket_name,
        base_path=base_path,
        secure=False
    )

    # ------ 原生客户端使用 ------
    print(minio_client.client.list_buckets())
    print(minio_client.client.bucket_exists(bucket_name))

    # 从文件上传对象
    obj_name = f"{base_path}/README.md"
    file_path = "README.md"
    r = minio_client.client.fput_object(bucket_name=bucket_name, object_name=obj_name, file_path=file_path, content_type="text/plain")
    print(r.bucket_name)
    print(r.object_name)
    print(r.location)
    print(r.etag)

    # 直接下载对象，并存入 file_path_download 指定的文件里，会覆盖已有文件
    file_path_download = "minio-" + file_path
    res_obj = minio_client.client.fget_object(bucket_name=bucket_name, object_name=obj_name, file_path=file_path_download)
    print(res_obj.bucket_name)
    print(res_obj.object_name)
    print(res_obj.etag)

    response: HTTPResponse | None = None
    try:
        # 下载对象: <class 'urllib3.response.HTTPResponse'>
        response: HTTPResponse = minio_client.client.get_object(bucket_name, obj_name)

        # 通过 read() 方法读取对象内容
        print("response.isclosed(): ", response.isclosed())
        # 直接读取对象内容, read() 返回的是字节流，需要解码，并且只能读取一次
        content = response.read().decode("utf-8")
        print("response content:\n{}".format(content))
        print("response.isclosed(): ", response.isclosed())  # 读取一次就变成 True 了

        # 也可以使用 .data 属性获取，也是字节流，但是需要保证 HTTPResponse 没有关闭，并且可以读取多次
        response: HTTPResponse = minio_client.client.get_object(bucket_name, obj_name)
        print("response.isclosed(): ", response.isclosed())
        print("response.data:\n", response.data)
        print("response.data.decode:\n", response.data.decode("utf-8"))
        print("response.isclosed(): ", response.isclosed())
    finally:
        # 需要手动关闭响应流
        if response:
            response.close()
            response.release_conn()

    # --------- 自定义客户端使用 ---------
    obj_name = f"README.md"
    file_path = "README.md"
    file_path_download = "minio-" + file_path
    minio_client.delete_object(object_name=obj_name)

    obj_res = minio_client.upload_file(object_name=obj_name, file_path=file_path)
    print(obj_res.bucket_name)
    print(obj_res.object_name)
    print(obj_res.etag)
    print(obj_res.location)

    obj_stat = minio_client.download_file(object_name=obj_name, file_path=file_path_download)
    print(obj_stat.bucket_name)
    print(obj_stat.object_name)
    print(obj_stat.etag)

    with open(file_path, "rb") as f:
        data = f.read()
    obj_res = minio_client.upload_object(object_name=obj_name, data=data, content_type="text/plain")
    print(obj_res.bucket_name)
    print(obj_res.object_name)
    print(obj_res.etag)

    data_stream = minio_client.get_object(object_name=obj_name)
    print(data_stream.decode('utf-8'))

    url = minio_client.get_presigned_url(object_name=obj_name)
    print(url)
