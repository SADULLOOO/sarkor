from django.contrib import admin

from .models import Category, District


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_tg", "slug", "parent", "position", "is_active")
    list_editable = ("position", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name_ru", "name_tg", "slug")
    prepopulated_fields = {"slug": ("name_ru",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_tg", "slug", "position")
    list_editable = ("position",)
