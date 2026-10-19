from typing import Any

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.sections import TableSection

from django.contrib import admin, messages
from django.db import models
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import Truncator

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_BODY_PREVIEW_LENGTH = 60
INLINE_COMMENTS_PER_PAGE = 10
SECTION_HEIGHT = 300

POST_CHANGELIST_URL_NAME = "admin:blog_post_changelist"
COMMENT_CHANGELIST_URL_NAME = "admin:blog_comment_changelist"
COMMENT_POST_FILTER_PARAM = "post__id__exact"

STATUS_LABEL_COLORS = {
    Post.Status.PUBLISHED.value: "success",  # green
    Post.Status.DRAFT.value: "warning",  # orange
}


def redirect_back(request: HttpRequest, fallback_url_name: str) -> HttpResponse:
    """Go back to the page the action was started from (keeps filters and page)."""
    referer = request.headers.get("referer")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect(fallback_url_name)


def short_text(text: str) -> str:
    return Truncator(text).chars(COMMENT_BODY_PREVIEW_LENGTH)


# ---------------------------------------------------------------- Category and Tag


class CategoryPostsSection(TableSection):
    """Expandable row: the posts of this category."""

    verbose_name = "Posts"
    related_name = "posts"
    fields = ["title", "status", "created_at"]
    height = SECTION_HEIGHT


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "posts_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_sections = [CategoryPostsSection]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Category]:
        return (
            super()
            .get_queryset(request)
            .annotate(_posts_count=Count("posts"))
            .prefetch_related("posts")
        )

    @display(description="Posts", ordering="_posts_count")
    def posts_count(self, obj: Category) -> int:
        return obj._posts_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ["name", "slug", "posts_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Tag]:
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    @display(description="Posts", ordering="_posts_count")
    def posts_count(self, obj: Tag) -> int:
        return obj._posts_count


# ---------------------------------------------------------------- Comment


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ["post_title", "author", "short_body", "created_at"]
    list_select_related = ["post", "author"]
    list_filter = [
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    search_fields = ["body", "author__email", "post__title"]
    autocomplete_fields = ["post", "author"]

    @display(description="Post", ordering="post__title")
    def post_title(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Comment")
    def short_body(self, obj: Comment) -> str:
        return short_text(obj.body)


# ---------------------------------------------------------------- Post


class PostCommentsSection(TableSection):
    """Expandable row: the comments of this post."""

    verbose_name = "Comments"
    related_name = "comments"
    fields = ["author", "short_body", "created_at"]
    height = SECTION_HEIGHT

    @display(description="Comment")
    def short_body(self, obj: Comment) -> str:
        return short_text(obj.body)


class CommentInline(TabularInline):
    model = Comment
    tab = True
    per_page = INLINE_COMMENTS_PER_PAGE
    extra = 0
    fields = ["author", "body", "created_at"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["author"]


@admin.register(Post)
class PostAdmin(ModelAdmin):
    # ---- list page
    list_display = [
        "header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count",
        "created_at",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    list_filter_submit = True
    search_fields = ["title", "body", "author__email"]
    list_sections = [PostCommentsSection]

    # ---- actions
    actions = ["publish_selected", "move_to_drafts"]  # bulk, with checkboxes
    actions_row = ["toggle_publish"]  # in every row
    actions_list = ["publish_all_drafts"]  # above the list
    actions_detail = ["open_comments"]  # on the post page
    actions_submit_line = ["save_and_publish"]  # next to the Save button

    # ---- edit page
    fieldsets = (
        ("Content", {"classes": ["tab"], "fields": ("title", "slug", "body")}),
        ("Classification", {"classes": ["tab"], "fields": ("category", "tags", "status")}),
        ("Meta", {"classes": ["tab"], "fields": ("author", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["author", "category", "tags"]
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    warn_unsaved_form = True
    inlines = [CommentInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Post]:
        return (
            super()
            .get_queryset(request)
            .select_related("author", "category")
            .prefetch_related(
                "tags",
                Prefetch("comments", queryset=Comment.objects.select_related("author")),
            )
            .annotate(_comments_count=Count("comments", distinct=True))
        )

    # ---- list columns

    @display(description="Post", header=True, ordering="title")
    def header(self, obj: Post) -> list[str]:
        author = obj.author
        initials = f"{author.first_name[:1]}{author.last_name[:1]}"
        return [obj.title, author.full_name, initials]

    @display(
        description="Status",
        ordering="status",
        label={value: color for value, color in STATUS_LABEL_COLORS.items()},
    )
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict[str, Any]:
        # len() uses the prefetched tags; .count() would query the database for every row.
        tags = obj.tags.all()
        return {
            "title": f"{len(tags)} tags",
            "items": [{"title": tag.name} for tag in tags],
            "striped": True,
        }

    @display(description="Comments", ordering="_comments_count")
    def comments_count(self, obj: Post) -> int:
        return obj._comments_count

    # ---- bulk actions

    @action(description="Publish selected", permissions=["change"])
    def publish_selected(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = self._set_status(queryset, Post.Status.PUBLISHED)
        self.message_user(request, f"Published posts: {updated}.", messages.SUCCESS)

    @action(description="Move to drafts", permissions=["change"])
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet[Post]) -> None:
        updated = self._set_status(queryset, Post.Status.DRAFT)
        self.message_user(request, f"Moved to drafts: {updated}.", messages.SUCCESS)

    @staticmethod
    def _set_status(queryset: QuerySet[Post], status: str) -> int:
        # update() skips auto_now, so refresh updated_at by hand.
        return queryset.update(status=status, updated_at=timezone.now())

    # ---- row action

    @action(description="Publish / unpublish", permissions=["change"])
    def toggle_publish(self, request: HttpRequest, object_id: int) -> HttpResponse:
        post = get_object_or_404(Post, pk=object_id)
        if post.status == Post.Status.PUBLISHED:
            post.status = Post.Status.DRAFT
            message = f"“{post.title}” moved to drafts."
        else:
            post.status = Post.Status.PUBLISHED
            message = f"“{post.title}” published."
        post.save(update_fields=["status", "updated_at"])
        self.message_user(request, message, messages.SUCCESS)
        return redirect_back(request, POST_CHANGELIST_URL_NAME)

    # ---- list action

    @action(description="Publish all drafts", permissions=["change"])
    def publish_all_drafts(self, request: HttpRequest) -> HttpResponse:
        updated = self._set_status(
            Post.objects.filter(status=Post.Status.DRAFT), Post.Status.PUBLISHED
        )
        self.message_user(request, f"Published drafts: {updated}.", messages.SUCCESS)
        return redirect_back(request, POST_CHANGELIST_URL_NAME)

    # ---- detail action

    @action(description="Open comments", permissions=["view"])
    def open_comments(self, request: HttpRequest, object_id: int) -> HttpResponse:
        url = reverse(COMMENT_CHANGELIST_URL_NAME)
        return redirect(f"{url}?{COMMENT_POST_FILTER_PARAM}={object_id}")

    # ---- submit line action (runs after the post is saved)

    @action(description="Save & publish", permissions=["change"])
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = Post.Status.PUBLISHED
        obj.save(update_fields=["status", "updated_at"])
        self.message_user(request, f"“{obj.title}” saved and published.", messages.SUCCESS)
