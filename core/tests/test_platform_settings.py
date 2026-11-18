from decimal import Decimal

import pytest

from core.models import PlatformSettings

pytestmark = pytest.mark.django_db


def test_load_creates_defaults():
    settings = PlatformSettings.load()

    assert settings.pk == 1
    assert settings.newbie_budget_limit == Decimal("500")
    assert settings.max_responses_per_task == 15


def test_always_one_row():
    PlatformSettings.load()
    PlatformSettings(max_responses_per_task=10).save()

    assert PlatformSettings.objects.count() == 1
    assert PlatformSettings.load().max_responses_per_task == 10


def test_admin_list_redirects_to_edit_page(admin_client):
    response = admin_client.get("/admin/core/platformsettings/")

    assert response.status_code == 302
    assert response.url.endswith("/admin/core/platformsettings/1/change/")
