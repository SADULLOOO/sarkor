from django.contrib import admin

from .models import Response, Review, Task, TaskPhoto


class TaskPhotoInline(admin.TabularInline):
    model = TaskPhoto
    extra = 0


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    raw_id_fields = ("executor",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__", "type", "category", "district", "budget", "status", "created_at")
    list_filter = ("status", "type", "category", "district")
    search_fields = ("description", "customer__phone", "executor__phone")
    raw_id_fields = ("customer", "executor")
    date_hierarchy = "created_at"
    inlines = [TaskPhotoInline, ResponseInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "target", "rating", "created_at")
    list_filter = ("rating",)
    raw_id_fields = ("task", "author", "target")
