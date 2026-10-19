#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path

from decouple import Config, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / "settings" / ".env"
ENV_ID_VARIABLE = "BLOG_ENV_ID"
DEFAULT_ENV_ID = "local"
SETTINGS_MODULE_TEMPLATE = "settings.env.{env_id}"


def get_env_id() -> str:
    """Read BLOG_ENV_ID from settings/.env (falls back to the OS environment)."""
    if ENV_FILE.exists():
        config = Config(RepositoryEnv(str(ENV_FILE)))
        return config(ENV_ID_VARIABLE, default=DEFAULT_ENV_ID)
    return os.environ.get(ENV_ID_VARIABLE, DEFAULT_ENV_ID)


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        SETTINGS_MODULE_TEMPLATE.format(env_id=get_env_id()),
    )
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and is your virtual environment activated?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
