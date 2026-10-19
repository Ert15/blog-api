"""Local development settings."""

from settings.base import *  # noqa: F403
from settings.conf import BASE_DIR

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Uncomment to print every SQL query (use it to check for N+1 problems):
# LOGGING["loggers"] = {  # noqa: F405
#     "django.db.backends": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
# }
