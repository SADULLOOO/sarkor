from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeForm, UserCreationForm
from .models import ExecutorProfile, PortfolioPhoto, User


class ExecutorProfileInline(admin.StackedInline):
    model = ExecutorProfile
    can_delete = False
    filter_horizontal = ("categories", "districts")
    readonly_fields = ("rating", "reviews_count", "completed_count")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = [ExecutorProfileInline]

    def get_inlines(self, request, obj):
        # Only phone and password on the "add user" page.
        return self.inlines if obj else []

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
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "password1", "password2"),
            },
        ),
    )


class PortfolioPhotoInline(admin.TabularInline):
    model = PortfolioPhoto
    extra = 0


@admin.register(ExecutorProfile)
class ExecutorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rating", "completed_count", "available_now", "updated_at")
    list_filter = ("available_now", "categories", "districts")
    search_fields = ("user__phone", "user__name")
    filter_horizontal = ("categories", "districts")
    readonly_fields = ("rating", "reviews_count", "completed_count", "created_at", "updated_at")
    inlines = [PortfolioPhotoInline]
