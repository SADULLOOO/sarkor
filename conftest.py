import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


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


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def api_client():
    return APIClient()


def client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def user(db):
    return User.objects.create_user("+992901234567")


@pytest.fixture
def auth_client(user):
    return client_for(user)


def make_image(name="photo.png", size=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")
