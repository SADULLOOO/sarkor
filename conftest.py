import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def test_cache(settings):
    # Separate Redis db so tests don't wipe the dev cache.
    settings.CACHES = {
        "default": {
            **settings.CACHES["default"],
            "LOCATION": "redis://127.0.0.1:6379/15",
        }
    }
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()
