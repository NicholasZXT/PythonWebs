"""
ASGI config for blog project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideablog.settings')
env_profile = os.environ.get('IDEA_BLOG_PROFILE', 'dev')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'ideablog.settings.{env_profile}')

application = get_asgi_application()
