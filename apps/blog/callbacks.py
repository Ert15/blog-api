"""Callbacks used by the UNFOLD setting (environment badge, sidebar, tabs, dashboard).

This module is referenced by dotted paths from settings, so models are imported
inside the functions: importing them at module level would break settings loading.
"""

import json
from typing import Any

from django.db.models import Count, Q
from django.http import HttpRequest
from django.urls import reverse

from settings.conf import BLOG_ENV_ID, ENV_ID_PROD

ENVIRONMENT_LOCAL_LABEL = "Local"
ENVIRONMENT_LOCAL_VARIANT = "warning"  # orange
ENVIRONMENT_PROD_LABEL = "Production"
ENVIRONMENT_PROD_VARIANT = "danger"  # red

POST_CHANGELIST_URL_NAME = "admin:blog_post_changelist"
STATUS_QUERY_PARAM = "status__exact"

TOP_AUTHORS_LIMIT = 5
PERCENT = 100
CHART_BAR_COLOR = "var(--color-primary-600)"


def environment_callback(request: HttpRequest) -> list[str]:
    """Badge in the header: Local (orange) or Production (red)."""
    if BLOG_ENV_ID == ENV_ID_PROD:
        return [ENVIRONMENT_PROD_LABEL, ENVIRONMENT_PROD_VARIANT]
    return [ENVIRONMENT_LOCAL_LABEL, ENVIRONMENT_LOCAL_VARIANT]


def sidebar_navigation(request: HttpRequest) -> list[dict[str, Any]]:
    """The sidebar menu. "Users & Access" is added for superusers only.

    It is built here (and not as a static list in settings) so the whole group,
    including its title, disappears for everybody else.
    """
    navigation: list[dict[str, Any]] = [
        {
            "title": "Overview",
            "separator": True,
            "items": [
                {"title": "Dashboard", "icon": "dashboard", "link": reverse("admin:index")},
            ],
        },
        {
            "title": "Content",
            "separator": True,
            "items": [
                {
                    "title": "Posts",
                    "icon": "article",
                    "link": reverse(POST_CHANGELIST_URL_NAME),
                    "badge": "apps.blog.callbacks.drafts_badge",  # number of drafts
                    "badge_variant": "warning",
                },
                {
                    "title": "Comments",
                    "icon": "chat",
                    "link": reverse("admin:blog_comment_changelist"),
                },
                {
                    "title": "Categories",
                    "icon": "category",
                    "link": reverse("admin:blog_category_changelist"),
                },
                {"title": "Tags", "icon": "sell", "link": reverse("admin:blog_tag_changelist")},
            ],
        },
    ]

    if request.user.is_superuser:
        navigation.append(
            {
                "title": "Users & Access",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "person",
                        "link": reverse("admin:auths_user_changelist"),
                    },
                    {
                        "title": "Groups",
                        "icon": "group",
                        "link": reverse("admin:auth_group_changelist"),
                    },
                ],
            }
        )

    return navigation


def drafts_badge(request: HttpRequest) -> int:
    """Number of drafts shown next to "Posts" in the sidebar."""
    from apps.blog.models import Post

    return Post.objects.filter(status=Post.Status.DRAFT).count()


def tabs_callback(request: HttpRequest) -> list[dict[str, Any]]:
    """Tabs All / Published / Drafts above the post list.

    Links are built from the request, because ``reverse_lazy(...) + "?..."``
    crashes when settings are loaded.
    """
    from apps.blog.models import Post

    changelist_url = reverse(POST_CHANGELIST_URL_NAME)
    current_status = request.GET.get(STATUS_QUERY_PARAM)

    return [
        {
            "models": ["blog.post"],
            "items": [
                {
                    "title": "All",
                    "link": changelist_url,
                    "active": current_status is None,
                },
                {
                    "title": "Published",
                    "link": f"{changelist_url}?{STATUS_QUERY_PARAM}={Post.Status.PUBLISHED}",
                },
                {
                    "title": "Drafts",
                    "link": f"{changelist_url}?{STATUS_QUERY_PARAM}={Post.Status.DRAFT}",
                },
            ],
        }
    ]


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Data for the admin home page. Everything is counted in the database."""
    from django.contrib.auth import get_user_model

    from apps.blog.models import Category, Comment, Post

    user_model = get_user_model()

    post_counts = Post.objects.aggregate(
        published=Count("id", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.Status.DRAFT)),
    )
    published: int = post_counts["published"]
    drafts: int = post_counts["drafts"]
    total_posts = published + drafts

    published_percent = round(published * PERCENT / total_posts) if total_posts else 0
    draft_percent = PERCENT - published_percent if total_posts else 0

    cards = [
        {"title": "Users", "value": user_model.objects.count(), "icon": "group"},
        {"title": "Published posts", "value": published, "icon": "article"},
        {"title": "Drafts", "value": drafts, "icon": "edit_note"},
        {"title": "Comments", "value": Comment.objects.count(), "icon": "chat"},
    ]

    categories = Category.objects.annotate(posts_total=Count("posts")).order_by("name")
    chart = {
        "labels": [category.name for category in categories],
        "datasets": [
            {
                "label": "Posts",
                "data": [category.posts_total for category in categories],
                "backgroundColor": CHART_BAR_COLOR,
                "borderRadius": 4,
            }
        ],
    }

    top_authors = (
        user_model.objects.annotate(posts_total=Count("posts"))
        .filter(posts_total__gt=0)
        .order_by("-posts_total", "email")[:TOP_AUTHORS_LIMIT]
    )
    top_authors_table = {
        "headers": ["Author", "Email", "Posts"],
        "rows": [[author.full_name, author.email, author.posts_total] for author in top_authors],
    }

    context.update(
        {
            "cards": cards,
            "posts_chart": json.dumps(chart),
            "top_authors_table": top_authors_table,
            "published_percent": published_percent,
            "draft_percent": draft_percent,
            "published_count": published,
            "drafts_count": drafts,
        }
    )
    return context
