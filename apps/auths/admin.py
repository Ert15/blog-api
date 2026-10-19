from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import (
    AdminPasswordChangeForm,
)
from unfold.forms import (
    UserChangeForm as UnfoldUserChangeForm,
)
from unfold.forms import (
    UserCreationForm as UnfoldUserCreationForm,
)

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from apps.auths.models import User

# Django's user forms and UserAdmin are built for a model with "username".
# Ours logs in with email, so the forms get our model and every "username"
# reference below is replaced.


class UserCreationForm(UnfoldUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeForm(UnfoldUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    # ---- list page
    ordering = ["email"]
    list_display = ["header", "active_label", "staff_label", "posts_count"]
    list_filter = [
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    ]
    list_filter_submit = True
    search_fields = ["email", "first_name", "last_name"]
    actions = ["activate_users", "deactivate_users"]

    # ---- edit page (tabs)
    fieldsets = (
        (
            "Personal info",
            {"classes": ["tab"], "fields": ("email", "password", "first_name", "last_name")},
        ),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        ("Important dates", {"classes": ["tab"], "fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ["last_login", "date_joined"]

    # ---- "add user" page
    add_fieldsets = (
        (
            None,
            {
                "classes": ["wide"],
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).annotate(_posts_count=Count("posts"))

    # ---- list columns

    @display(description="User", header=True, ordering="email")
    def header(self, obj: User) -> list[str]:
        initials = f"{obj.first_name[:1]}{obj.last_name[:1]}"
        return [obj.full_name, obj.email, initials]

    @display(
        description="Active",
        ordering="is_active",
        label={"active": "success", "inactive": "danger"},
    )
    def active_label(self, obj: User) -> tuple[str, str]:
        return ("active", "Active") if obj.is_active else ("inactive", "Inactive")

    @display(
        description="Staff",
        ordering="is_staff",
        label={"staff": "info", "regular": ""},
    )
    def staff_label(self, obj: User) -> tuple[str, str]:
        return ("staff", "Staff") if obj.is_staff else ("regular", "Regular")

    @display(description="Posts", ordering="_posts_count")
    def posts_count(self, obj: User) -> int:
        return obj._posts_count

    # ---- bulk actions

    @action(description="Activate selected users", permissions=["change"])
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated users: {updated}.", messages.SUCCESS)

    @action(description="Deactivate selected users", permissions=["change"])
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        # Never let someone lock themselves out of the admin.
        updated = queryset.exclude(pk=request.user.pk).update(is_active=False)
        self.message_user(request, f"Deactivated users: {updated}.", messages.SUCCESS)


# Groups use Django's plain admin by default and look broken with Unfold.
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
