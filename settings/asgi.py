"""ASGI config for the blog project."""

import os

from django.core.asgi import get_asgi_application

from settings.conf import BLOG_ENV_ID

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{BLOG_ENV_ID}")

application = get_asgi_application()
