import random
import time
from datetime import datetime, timedelta
from typing import Any

from faker import Faker

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

# Default counts
DEFAULT_USERS = 20
DEFAULT_POSTS = 100
DEFAULT_COMMENTS = 500

# Users
SEED_PASSWORD = "seedpass123"
EMAIL_DOMAIN = "example.com"
INACTIVE_USER_RATIO = 0.15
STAFF_USER_RATIO = 0.10

# Posts
PUBLISHED_POST_RATIO = 0.70
NO_CATEGORY_POST_RATIO = 0.10
MIN_TAGS_PER_POST = 0
MAX_TAGS_PER_POST = 5
MIN_POST_PARAGRAPHS = 3
MAX_POST_PARAGRAPHS = 6
POST_TITLE_WORDS = 6
POST_AGE_DAYS = 365
FIRST_SLUG_SUFFIX = 2

# Comments
MIN_COMMENT_SENTENCES = 1
MAX_COMMENT_SENTENCES = 3

# Output
SUMMARY_LABEL_WIDTH = 11
SUMMARY_COUNT_WIDTH = 4
ELAPSED_DECIMALS = 2

CATEGORY_NAMES = [
    "Python",
    "Django",
    "DevOps",
    "Databases",
    "Frontend",
    "Testing",
    "Security",
    "Career",
]

TAG_NAMES = [
    "tutorial",
    "beginners",
    "best-practices",
    "performance",
    "docker",
    "postgresql",
    "rest-api",
    "orm",
    "async",
    "caching",
    "deployment",
    "git",
    "linux",
    "ci-cd",
    "debugging",
    "refactoring",
    "architecture",
    "tips",
    "cheatsheet",
    "open-source",
]


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users", type=int, default=DEFAULT_USERS, help="Number of users to create"
        )
        parser.add_argument(
            "--posts", type=int, default=DEFAULT_POSTS, help="Number of posts to create"
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding (superusers are kept)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        self._validate(users_count, posts_count, comments_count, clear)

        started_at = time.perf_counter()
        fake = Faker()

        with transaction.atomic():
            if clear:
                self._clear()
                self.stdout.write("Existing data deleted (superusers kept).")

            users_created = self._create_users(fake, users_count)
            categories_created = self._create_categories()
            tags_created = self._create_tags()
            posts_created = self._create_posts(fake, posts_count)
            comments_created = self._create_comments(fake, comments_count)

        elapsed = time.perf_counter() - started_at
        self._print_summary(
            users_created, categories_created, tags_created, posts_created, comments_created
        )
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.{ELAPSED_DECIMALS}f} seconds"))

    # ------------------------------------------------------------------ validation

    def _validate(self, users: int, posts: int, comments: int, clear: bool) -> None:
        """Check the arguments before anything is written to the database."""
        for name, value in (("users", users), ("posts", posts), ("comments", comments)):
            if value < 0:
                raise CommandError(f"--{name} must not be negative (got {value}).")

        users_after = users + (
            User.objects.filter(is_superuser=True).count() if clear else User.objects.count()
        )
        if (posts or comments) and users_after == 0:
            raise CommandError(
                "Posts and comments need authors, but there are no users. "
                "Use --users with a number greater than 0."
            )

        if comments:
            existing_published = (
                0 if clear else Post.objects.filter(status=Post.Status.PUBLISHED).count()
            )
            if existing_published + self._published_count(posts) == 0:
                raise CommandError(
                    "Comments are requested, but there are no published posts. "
                    "Use --posts with a number greater than 0."
                )

    @staticmethod
    def _published_count(posts: int) -> int:
        return round(posts * PUBLISHED_POST_RATIO)

    # ------------------------------------------------------------------ clearing

    @staticmethod
    def _clear() -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Tag.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    # ------------------------------------------------------------------ users

    def _create_users(self, fake: Faker, count: int) -> int:
        if count == 0:
            return 0

        used_emails: set[str] = set(User.objects.values_list("email", flat=True))
        hashed_password = make_password(SEED_PASSWORD)  # hash once: hashing is slow on purpose

        users: list[Any] = []
        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = self._unique_email(first_name, last_name, used_emails)
            users.append(
                User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=hashed_password,
                    is_active=random.random() >= INACTIVE_USER_RATIO,
                    is_staff=random.random() < STAFF_USER_RATIO,
                )
            )

        return len(User.objects.bulk_create(users))

    @staticmethod
    def _unique_email(first_name: str, last_name: str, used_emails: set[str]) -> str:
        local_part = slugify(f"{first_name} {last_name}").replace("-", ".")
        email = f"{local_part}@{EMAIL_DOMAIN}"
        suffix = FIRST_SLUG_SUFFIX
        while email in used_emails:
            email = f"{local_part}{suffix}@{EMAIL_DOMAIN}"
            suffix += 1
        used_emails.add(email)
        return email

    # ------------------------------------------------------------------ categories and tags

    def _create_categories(self) -> int:
        return self._create_named(Category, CATEGORY_NAMES)

    def _create_tags(self) -> int:
        return self._create_named(Tag, TAG_NAMES)

    @staticmethod
    def _create_named(model: type[Category] | type[Tag], names: list[str]) -> int:
        """Create the rows that do not exist yet; skip the ones that do."""
        existing_names = set(model.objects.values_list("name", flat=True))
        existing_slugs = set(model.objects.values_list("slug", flat=True))

        new_rows = []
        for name in names:
            slug = slugify(name)
            if name in existing_names or slug in existing_slugs:
                continue
            new_rows.append(model(name=name, slug=slug))

        return len(model.objects.bulk_create(new_rows))

    # ------------------------------------------------------------------ posts

    def _create_posts(self, fake: Faker, count: int) -> int:
        if count == 0:
            return 0

        author_ids = list(User.objects.values_list("id", flat=True))
        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())
        used_slugs: set[str] = set(Post.objects.values_list("slug", flat=True))
        slug_max_length: int = Post._meta.get_field("slug").max_length

        published = self._published_count(count)
        statuses = [Post.Status.PUBLISHED] * published + [Post.Status.DRAFT] * (count - published)
        random.shuffle(statuses)

        now = timezone.now()
        posts: list[Post] = []
        for status in statuses:
            title = fake.sentence(nb_words=POST_TITLE_WORDS).rstrip(".")
            has_category = categories and random.random() >= NO_CATEGORY_POST_RATIO
            posts.append(
                Post(
                    author_id=random.choice(author_ids),
                    title=title,
                    slug=self._unique_slug(title, used_slugs, slug_max_length),
                    body="\n\n".join(
                        fake.paragraphs(nb=random.randint(MIN_POST_PARAGRAPHS, MAX_POST_PARAGRAPHS))
                    ),
                    category=random.choice(categories) if has_category else None,
                    status=status,
                )
            )

        created = Post.objects.bulk_create(posts)

        # auto_now_add always sets "now", so spread the dates afterwards.
        for post in created:
            post.created_at = self._random_datetime_between(
                now - timedelta(days=POST_AGE_DAYS), now
            )
        Post.objects.bulk_update(created, ["created_at"])

        if tags:
            for post in created:
                tags_count = random.randint(MIN_TAGS_PER_POST, min(MAX_TAGS_PER_POST, len(tags)))
                if tags_count:
                    post.tags.set(random.sample(tags, tags_count))

        return len(created)

    @staticmethod
    def _unique_slug(title: str, used_slugs: set[str], max_length: int) -> str:
        base = slugify(title)[:max_length].strip("-") or "post"
        slug = base
        suffix = FIRST_SLUG_SUFFIX
        while slug in used_slugs:
            suffix_text = f"-{suffix}"
            slug = f"{base[: max_length - len(suffix_text)].rstrip('-')}{suffix_text}"
            suffix += 1
        used_slugs.add(slug)
        return slug

    @staticmethod
    def _random_datetime_between(start: datetime, end: datetime) -> datetime:
        seconds = int((end - start).total_seconds())
        return start + timedelta(seconds=random.randint(0, max(seconds, 0)))

    # ------------------------------------------------------------------ comments

    def _create_comments(self, fake: Faker, count: int) -> int:
        if count == 0:
            return 0

        author_ids = list(User.objects.values_list("id", flat=True))
        published_posts = list(
            Post.objects.filter(status=Post.Status.PUBLISHED).values_list("id", "created_at")
        )
        now = timezone.now()

        comments: list[Comment] = []
        for _ in range(count):
            post_id, _post_created_at = random.choice(published_posts)
            comments.append(
                Comment(
                    post_id=post_id,
                    author_id=random.choice(author_ids),
                    body=" ".join(
                        fake.sentences(
                            nb=random.randint(MIN_COMMENT_SENTENCES, MAX_COMMENT_SENTENCES)
                        )
                    ),
                )
            )

        created = Comment.objects.bulk_create(comments)

        # Comments appear after their post, so keep the dates consistent.
        post_dates = dict(published_posts)
        for comment in created:
            comment.created_at = self._random_datetime_between(post_dates[comment.post_id], now)
        Comment.objects.bulk_update(created, ["created_at"])

        return len(created)

    # ------------------------------------------------------------------ output

    def _print_summary(
        self, users: int, categories: int, tags: int, posts: int, comments: int
    ) -> None:
        rows = (
            ("Users:", users),
            ("Categories:", categories),
            ("Tags:", tags),
            ("Posts:", posts),
            ("Comments:", comments),
        )
        for label, value in rows:
            self.stdout.write(
                f"{label:<{SUMMARY_LABEL_WIDTH}}{value:>{SUMMARY_COUNT_WIDTH}} created"
            )
