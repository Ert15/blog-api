"""Reads settings/.env and exports configuration variables."""

from pathlib import Path

from decouple import AutoConfig, Csv

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = BASE_DIR / "settings"

ENV_ID_LOCAL = "local"
ENV_ID_PROD = "prod"

config = AutoConfig(search_path=SETTINGS_DIR)

BLOG_ENV_ID: str = config("BLOG_ENV_ID", default=ENV_ID_LOCAL)
BLOG_SECRET_KEY: str = config("BLOG_SECRET_KEY", default="django-insecure-dev-only-key")
BLOG_ALLOWED_HOSTS: list[str] = config(
    "BLOG_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

BLOG_GITHUB_URL: str = config(
    "BLOG_GITHUB_URL", default="https://github.com/your-username/blog-api"
)

BLOG_DB_NAME: str = config("BLOG_DB_NAME", default="blog")
BLOG_DB_USER: str = config("BLOG_DB_USER", default="blog")
BLOG_DB_PASSWORD: str = config("BLOG_DB_PASSWORD", default="")
BLOG_DB_HOST: str = config("BLOG_DB_HOST", default="localhost")
BLOG_DB_PORT: str = config("BLOG_DB_PORT", default="5432")
