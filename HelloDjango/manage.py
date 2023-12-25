#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

import pymysql
# 配置MySQL使用pymysql作为驱动
pymysql.install_as_MySQLdb()


def main():
    """Run administrative tasks."""
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideablog.settings')
    env_profile = os.environ.get('IDEA_BLOG_PROFILE', 'dev')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'ideablog.settings.{env_profile}')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # 设置本地运行时的端口号
    from django.core.management.commands.runserver import Command as runserver
    runserver.default_port = "8100"
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
