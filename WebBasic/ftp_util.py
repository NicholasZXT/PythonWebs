import os
from typing import List, Optional
from io import BytesIO, StringIO
from functools import wraps
import ftplib


class FTPUtil:
    """
    FTP工具类，用于读写指定文件夹中的文件
    """
    def __init__(self, host: str, username: str, password: str, port: int = 21, encoding: str = 'utf-8', raise_error: bool = False):
        """
        host: FTP服务器地址
        username: 用户名
        password: 密码
        port: 端口号，默认为21
        encoding: 编码格式，默认为utf-8
        raise_error: 是否抛出异常，默认为False
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.encoding = encoding
        self.raise_error = raise_error
        self.ftp = None

    @staticmethod
    def _handle_ftp_exception(message: str, default_return=None):
        """
        统一处理FTP操作异常
        Args:
            message: 错误信息前缀
            default_return: 出错时的默认返回值
        """
        def decorator(func):
            @wraps(func)
            def wrapper(self: 'FTPUtil', *args, **kwargs):
                # 获取raise_error参数值
                raise_error = kwargs.get('raise_error', None)
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    # 调用统一处理异常方法
                    self._handle_exception(e, message, raise_error)
                    # 不抛出异常时返回对应类型的默认值
                    if default_return is not None:
                        return default_return
                    # 根据函数注解推测返回类型
                    return_type = func.__annotations__.get('return')
                    if return_type == bool:
                        return False
                    elif return_type == List[str]:
                        return []
                    elif 'Optional' in str(return_type):
                        return None
                    return None
            return wrapper

        return decorator

    def _handle_exception(self, e: Exception, message: str, raise_error: Optional[bool] = None):
        """
        统一处理异常
        Args:
            e: 捕获的异常
            message: 错误信息前缀
            raise_error: 是否抛出异常，None时表示使用实例默认值
        """
        raise_error = raise_error if raise_error is not None else self.raise_error
        error_message = f"{message}: {e}"
        print(error_message)
        if raise_error:
            try:
                # 尝试最常见的异常构造方式 (e.g., ValueError(msg))
                raise type(e)(error_message) from e
            except TypeError:
                # 如果上面的方式失败（TypeError: function takes exactly X arguments），则直接链接并重新抛出原始异常
                raise e from e

    def connect(self, raise_error: Optional[bool] = None) -> bool:
        """
        Returns:
            bool: 连接是否成功
        """
        try:
            self.ftp = ftplib.FTP()
            self.ftp.encoding = self.encoding
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.username, self.password)
            return True
        except Exception as e:
            self._handle_exception(e, "连接FTP服务器失败", raise_error)
            return False

    def disconnect(self, raise_error: Optional[bool] = None):
        """
        断开FTP连接
        """
        if self.ftp:
            try:
                self.ftp.quit()
            except Exception as e:
                try:
                    self.ftp.close()
                except Exception as close_e:
                    self._handle_exception(close_e, "关闭FTP连接失败", raise_error)
            finally:
                self.ftp = None

    @_handle_ftp_exception("切换目录失败", default_return=False)
    def change_directory(self, directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        切换到指定目录
        Args:
            directory: 目标目录路径
            raise_error:
        Returns:
            bool: 切换是否成功
        """
        self.ftp.cwd(directory)
        return True

    @_handle_ftp_exception("创建目录失败", default_return=False)
    def create_directory(self, directory_name: str, parent_directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        在指定目录下创建新目录
        Args:
            directory_name: 新目录名称
            parent_directory: 父目录
            raise_error:
        Returns:
            bool: 创建是否成功
        """
        # 切换到父目录
        if not self.change_directory(parent_directory, raise_error):
            return False
        # 创建新目录
        self.ftp.mkd(directory_name)
        return True

    @_handle_ftp_exception("创建目录失败", default_return=False)
    def create_directory_recursive(self, directory_path: str, raise_error: Optional[bool] = None) -> bool:
        """
        递归创建目录，支持创建多级目录
        Args:
            directory_path: 要创建的目录路径（可以是多级目录）
            raise_error:
        Returns:
            bool: 创建是否成功
        """
        # 标准化路径分隔符
        directory_path = directory_path.replace('\\', '/')
        # 如果是绝对路径，先切换到根目录
        if directory_path.startswith('/'):
            try:
                self.ftp.cwd('/')
                directory_path = directory_path[1:]  # 去掉开头的 '/'
            except Exception as e:
                self._handle_exception(e, "切换到根目录失败", raise_error)
                return False
        # 分割路径
        path_parts = [part for part in directory_path.split('/') if part]
        # 逐级创建目录
        for part in path_parts:
            try:
                # 尝试切换到当前目录
                self.ftp.cwd(part)
            except ftplib.error_perm:
                # 如果目录不存在，则创建它
                try:
                    self.ftp.mkd(part)
                    # 创建成功后切换到该目录
                    self.ftp.cwd(part)
                except Exception as e:
                    self._handle_exception(e, f"创建目录 {part} 失败", raise_error)
                    return False
            except Exception as e:
                self._handle_exception(e, f"切换到目录 {part} 失败", raise_error)
                return False
        return True

    @_handle_ftp_exception("获取文件列表失败", default_return=[])
    def list_files(self, directory: str = None, raise_error: Optional[bool] = None) -> List[str]:
        """
        列出指定目录下的文件列表
        Args:
            directory: 目录路径，如果为None则使用当前目录
            raise_error:
        Returns:
            List[str]: 文件名列表
        """
        original_dir = self.ftp.pwd()
        if directory:
            self.ftp.cwd(directory)
        files = self.ftp.nlst()
        self.ftp.cwd(original_dir)
        return files

    @_handle_ftp_exception("上传文件失败", default_return=False)
    def upload_file(self, local_path: str, directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        上传文件到FTP服务器指定目录
        Args:
            local_path: 本地文件路径
            directory: 远程目标目录
            raise_error:
        Returns:
            bool: 上传是否成功
        """
        # 检查本地文件是否存在
        if not os.path.exists(local_path):
            error_message = f"本地文件不存在: {local_path}"
            print(error_message)
            raise_error = raise_error if raise_error else self.raise_error
            if raise_error:
                raise FileNotFoundError(error_message)
            return False
        if directory:
            # 切换到目标目录
            if not self.change_directory(directory, raise_error):
                return False
        # 从本地路径提取文件名
        filename = os.path.basename(local_path)
        # 上传文件
        with open(local_path, 'rb') as file:
            self.ftp.storbinary(f"STOR {filename}", file)
        return True

    @_handle_ftp_exception("下载文件失败", default_return=False)
    def download_file(self, remote_path: str, directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        从FTP服务器下载文件
        Args:
            remote_path: 远程文件路径
            directory: 本地目录
            raise_error:
        Returns:
            bool: 下载是否成功
        """
        # 获取远程文件所在的目录
        remote_directory = os.path.dirname(remote_path)
        # 切换到源目录
        if not self.change_directory(remote_directory, raise_error):
            return False
        # 从远程路径提取文件名
        filename = os.path.basename(remote_path)
        # 构造完整的本地路径
        local_path = os.path.join(directory, filename)
        # 下载文件
        with open(local_path, 'wb') as file:
            self.ftp.retrbinary(f"RETR {remote_path}", file.write)
        return True

    @_handle_ftp_exception("上传目录失败", default_return=False)
    def upload_dir(self, local_directory: str, remote_directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        将本地指定文件夹内的所有文件（不包括子文件夹）上传到远端FTP的指定目录里
        Args:
            local_directory: 本地文件夹路径
            remote_directory: 远程目标目录路径
            raise_error:
        Returns:
            bool: 上传是否成功
        """
        # 检查本地目录是否存在
        if not os.path.exists(local_directory):
            error_message = f"本地目录不存在: {local_directory}"
            print(error_message)
            raise_error = raise_error if raise_error else self.raise_error
            if raise_error:
                raise FileNotFoundError(error_message)
            return False
        # 获取本地目录中的所有文件（不包括子目录）
        try:
            local_files = [f for f in os.listdir(local_directory) if os.path.isfile(os.path.join(local_directory, f))]
        except Exception as e:
            self._handle_exception(e, "读取本地目录失败", raise_error)
            return False

        # 切换到远程目录
        if not self.change_directory(remote_directory, raise_error):
            return False

        # 逐个上传文件
        for filename in local_files:
            local_path = os.path.join(local_directory, filename)
            try:
                with open(local_path, 'rb') as file:
                    self.ftp.storbinary(f"STOR {filename}", file)
            except Exception as e:
                self._handle_exception(e, f"上传文件 {filename} 失败", raise_error)
                if raise_error:
                    return False
                # 继续上传其他文件
        return True

    @_handle_ftp_exception("下载目录失败", default_return=False)
    def download_dir(self, remote_directory: str, local_directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        将远端FTP的指定目录里的所有文件（不包括子文件夹）下载到本地指定目录里
        Args:
            remote_directory: 远程源目录路径
            local_directory: 本地目标目录路径
            raise_error:
        Returns:
            bool: 下载是否成功
        """
        # 检查本地目录是否存在，不存在则创建
        if not os.path.exists(local_directory):
            try:
                os.makedirs(local_directory)
            except Exception as e:
                self._handle_exception(e, "创建本地目录失败", raise_error)
                return False
        # 获取远程目录中的所有文件
        try:
            remote_files = self.list_files(remote_directory, raise_error=raise_error)
        except Exception as e:
            self._handle_exception(e, "获取远程目录文件列表失败", raise_error)
            return False

        # 切换到远程目录
        if not self.change_directory(remote_directory, raise_error):
            return False

        # 逐个下载文件
        for filename in remote_files:
            local_path = os.path.join(local_directory, filename)
            try:
                with open(local_path, 'wb') as file:
                    self.ftp.retrbinary(f"RETR {filename}", file.write)
            except Exception as e:
                self._handle_exception(e, f"下载文件 {filename} 失败", raise_error)
                if raise_error:
                    return False
                # 继续下载其他文件
        return True

    @_handle_ftp_exception("读取文件内容失败", default_return=None)
    def read_file_content(self, remote_path: str, encoding: str = 'utf-8', raise_error: Optional[bool] = None) -> Optional[str]:
        """
        读取FTP服务器上文件的内容
        Args:
            remote_path: 远程文件完整路径
            encoding: 文件编码，默认为utf-8
            raise_error:
        Returns:
            Optional[str]: 文件内容，失败时返回None
        """
        # 从路径中提取目录和文件名
        remote_directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        # 如果有目录部分，则切换到该目录
        if remote_directory:
            if not self.change_directory(remote_directory, raise_error):
                return None
        # 读取文件内容到内存
        buffer = BytesIO()
        self.ftp.retrbinary(f"RETR {filename}", buffer.write)
        buffer.seek(0)
        content = buffer.read().decode(encoding)
        return content

    @_handle_ftp_exception("写入文件内容失败", default_return=False)
    def write_file_content(
            self,
            remote_path: str, content: str,
            encoding: str = 'utf-8', raise_error: Optional[bool] = None
    ) -> bool:
        """
        将内容写入FTP服务器上的文件
        Args:
            remote_path: 远程文件完整路径
            content: 要写入的内容
            encoding: 文件编码，默认为utf-8
            raise_error:
        Returns:
            bool: 写入是否成功
        """
        # 从路径中提取目录和文件名
        remote_directory = os.path.dirname(remote_path)
        filename = os.path.basename(remote_path)
        # 如果有目录部分，则切换到该目录
        if remote_directory:
            if not self.change_directory(remote_directory, raise_error):
                return False
        # 将内容写入文件
        buffer = BytesIO(content.encode(encoding))
        self.ftp.storbinary(f"STOR {filename}", buffer)
        return True

    @_handle_ftp_exception("删除文件失败", default_return=False)
    def delete_file(self, remote_path: str, directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        删除FTP服务器上的文件
        Args:
            remote_path: 远程文件路径
            directory: 文件所在目录
            raise_error:
        Returns:
            bool: 删除是否成功
        """
        # 切换到目标目录
        if not self.change_directory(directory, raise_error):
            return False
        # 删除文件
        self.ftp.delete(remote_path)
        return True

    @_handle_ftp_exception("删除空目录失败", default_return=False)
    def delete_directory(self, directory_name: str, parent_directory: str, raise_error: Optional[bool] = None) -> bool:
        """
        删除指定父目录下的一个空目录。
        Args:
            directory_name: 要删除的目录名称。
            parent_directory: 父目录路径。
            raise_error: 是否抛出异常。
        Returns:
            bool: 删除是否成功。
        """
        # 切换到父目录
        if not self.change_directory(parent_directory, raise_error):
            return False
        # 删除空目录
        self.ftp.rmd(directory_name)
        return True

    @_handle_ftp_exception("递归删除目录失败", default_return=False)
    def delete_directory_recursive(self, directory_path: str, raise_error: Optional[bool] = None) -> bool:
        """
        递归删除FTP服务器上的目录及其所有内容。
        Args:
            directory_path: 要删除的目录的完整路径 (相对于FTP根目录)。
            raise_error: 是否抛出异常。
        Returns:
            bool: 删除是否成功。
        """
        # --- 强制要求绝对路径 ---
        if not directory_path.startswith('/'):
            error_msg = f"请使用绝对路径: {directory_path}"
            self._handle_exception(ValueError(error_msg), error_msg, raise_error)
            return False

        # 记录原始工作目录
        original_wd = self.ftp.pwd()
        try:
            self.ftp.cwd(directory_path)
            # 获取目录内容列表 (使用 LIST 命令)
            entries = []
            self.ftp.retrlines('LIST', entries.append)
            # 遍历内容并删除
            for entry in entries:
                parts = entry.split(maxsplit=8)
                if len(parts) < 9:
                    continue  # 跳过格式不正确的行
                name = parts[-1]
                is_dir = parts[0].startswith('d')
                if is_dir:
                    # 递归删除子目录 (构建子目录的绝对路径)
                    subdir_path = f"{directory_path.rstrip('/')}/{name}"
                    if not self.delete_directory_recursive(subdir_path, raise_error):
                        return False
                else:
                    self.ftp.delete(name)

            # 内容删除完毕，切换回父目录准备删除目标目录本身
            parent_path = '/'.join(directory_path.rstrip('/').split('/')[:-1]) or '/'
            self.ftp.cwd(parent_path)
            # 删除现在为空的目标目录
            dir_name_to_delete = directory_path.rstrip('/').split('/')[-1]
            self.ftp.rmd(dir_name_to_delete)

            return True
        finally:
            # --- 清理：尝试恢复原始工作目录 ---
            self.ftp.cwd(original_wd)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def main():
    ...


if __name__ == "__main__":
    # 使用示例：使用上下文管理器方式
    ftp_config = {
        "host": "10.3.4.120",
        "username": "ftpuser",
        "password": "ftp-2025",
        # "encoding" : "gbk"  # 目录内容包含中文名称，则需要指定编码
    }
    # ftp_util = FTPUtil(**ftp_config)
    # ftp_util.connect()
    # ftp_util.disconnect()
    with FTPUtil(**ftp_config) as ftp_util:
        # 列出目录中的文件
        files = ftp_util.list_files()
        # files = ftp_util.list_files("/")
        print("文件列表:", files)
        # 上传文件
        ftp_util.create_directory("test", "/")
        ftp_util.upload_file("README.md", "test")
        # 上传文件-v2
        ftp_util.create_directory_recursive("/test-2/some")
        ftp_util.upload_file("README.md", "/test-2/some")
        # 下载文件
        ftp_util.download_file("/test/README.md", ".")
        # 读取文件内容
        content = ftp_util.read_file_content("/test/README.md")
        if content:
            print("文件内容:", content)
        # 写入文件内容
        ftp_util.write_file_content("/new_file.txt", "Hello, FTP!")
        # 上传文件夹
        ftp_util.upload_dir("util", "/test")
        # 下载文件夹
        ftp_util.download_dir("/test", "test")
        # 删除文件
        ftp_util.delete_file("README.md", "/test")
        # 删除目录
        ftp_util.delete_directory_recursive("/test-policy/some")
