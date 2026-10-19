"""Shared Django settings. Environment-specific values live in settings/env/."""

from settings.conf import BASE_DIR, BLOG_ALLOWED_HOSTS, BLOG_GITHUB_URL, BLOG_SECRET_KEY

SECRET_KEY = BLOG_SECRET_KEY
ALLOWED_HOSTS = BLOG_ALLOWED_HOSTS

INSTALLED_APPS = [
    # Unfold must be above django.contrib.admin, otherwise styles are not applied
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "apps.auths",
    "apps.blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"
ASGI_APPLICATION = "settings.asgi.application"

AUTH_USER_MODEL = "auths.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "blog.log",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}

# --------------------------------------------------------------------- Django Unfold

UNFOLD_DOCS_URL = "https://unfoldadmin.com/docs/"

UNFOLD = {
    "SITE_TITLE": "Blog API",
    "SITE_HEADER": "Blog API",
    "SITE_SUBHEADER": "Content administration",
    "SITE_SYMBOL": "edit_note",  # Material Symbols icon
    # Tailwind "emerald" palette
    "COLORS": {
        "primary": {
            "50": "oklch(97.9% 0.021 166.113)",
            "100": "oklch(95% 0.052 163.051)",
            "200": "oklch(90.5% 0.093 164.15)",
            "300": "oklch(84.5% 0.143 164.978)",
            "400": "oklch(76.5% 0.177 163.223)",
            "500": "oklch(69.6% 0.17 162.48)",
            "600": "oklch(59.6% 0.145 163.225)",
            "700": "oklch(50.8% 0.118 165.612)",
            "800": "oklch(43.2% 0.095 166.913)",
            "900": "oklch(37.8% 0.077 168.94)",
            "950": "oklch(26.2% 0.051 172.552)",
        },
    },
    "ENVIRONMENT": "apps.blog.callbacks.environment_callback",
    "SITE_DROPDOWN": [
        {"icon": "code", "title": "GitHub repository", "link": BLOG_GITHUB_URL},
        {"icon": "menu_book", "title": "Unfold docs", "link": UNFOLD_DOCS_URL},
    ],
    "COMMAND": {"search_models": True, "show_history": True},  # Cmd+K / Ctrl+K
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": "apps.blog.callbacks.sidebar_navigation",
    },
    "TABS": "apps.blog.callbacks.tabs_callback",  # All / Published / Drafts
    "DASHBOARD_CALLBACK": "apps.blog.callbacks.dashboard_callback",
}
