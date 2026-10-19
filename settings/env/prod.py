"""Production settings."""

from settings.base import *  # noqa: F403
from settings.conf import (
    BLOG_DB_HOST,
    BLOG_DB_NAME,
    BLOG_DB_PASSWORD,
    BLOG_DB_PORT,
    BLOG_DB_USER,
)

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": BLOG_DB_NAME,
        "USER": BLOG_DB_USER,
        "PASSWORD": BLOG_DB_PASSWORD,
        "HOST": BLOG_DB_HOST,
        "PORT": BLOG_DB_PORT,
    }
}
