from django.contrib import admin
from django.shortcuts import redirect

from .models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # One row only, so go straight to the edit page.
        obj = PlatformSettings.load()
        return redirect("admin:core_platformsettings_change", obj.pk)
