from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone", "name", "is_customer", "is_executor", "trust_level", "is_blocked", "date_joined")
    list_filter = ("is_customer", "is_executor", "trust_level", "is_blocked", "is_staff")
    search_fields = ("phone", "name")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Profile"), {"fields": ("name", "language")}),
        (_("Roles"), {"fields": ("is_customer", "is_executor")}),
        (_("Status"), {"fields": ("trust_level", "is_blocked", "is_active")}),
        (_("Permissions"), {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Dates"), {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2"),
        }),
    )