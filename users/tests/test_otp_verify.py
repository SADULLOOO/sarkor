import pytest
from django.core.cache import cache

from users.models import User
from users.services import OTP_MAX_ATTEMPTS

pytestmark = pytest.mark.django_db

PHONE = "+992901234567"
VERIFY_URL = "/api/v1/auth/otp/verify"


@pytest.fixture
def otp_code(api_client):
    api_client.post("/api/v1/auth/otp/request", {"phone": PHONE})
    return cache.get(f"otp:code:{PHONE}")


def wrong(code):
    return f"{(int(code) + 1) % 1_000_000:06d}"


def test_first_login_creates_user(api_client, otp_code):
    response = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code})

    assert response.status_code == 201
    assert response.data["is_new"] is True
    assert response.data["access"]
    assert response.data["refresh"]
    assert User.objects.filter(phone=PHONE).exists()


def test_existing_user_logs_in(api_client, otp_code):
    user = User.objects.create_user(PHONE, name="Ali")

    response = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code})

    assert response.status_code == 200
    assert response.data["is_new"] is False
    assert response.data["user"]["id"] == user.id


def test_code_works_only_once(api_client, otp_code):
    api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code})

    response = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code})

    assert response.status_code == 400


def test_wrong_code(api_client, otp_code):
    response = api_client.post(VERIFY_URL, {"phone": PHONE, "code": wrong(otp_code)})

    assert response.status_code == 400
    assert "code" in response.data["fields"]


def test_lock_after_too_many_wrong_attempts(api_client, otp_code):
    for _ in range(OTP_MAX_ATTEMPTS):
        api_client.post(VERIFY_URL, {"phone": PHONE, "code": wrong(otp_code)})

    # Even the right code is rejected while the phone is locked.
    response = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code})

    assert response.status_code == 429


def test_blocked_user_gets_no_tokens(api_client, otp_code):
    User.objects.create_user(PHONE, is_blocked=True)

    response = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code})

    assert response.status_code == 403
    assert "access" not in response.data


def test_refresh_rotates_token(api_client, otp_code):
    tokens = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code}).data

    response = api_client.post("/api/v1/auth/refresh", {"refresh": tokens["refresh"]})

    assert response.status_code == 200
    assert response.data["refresh"] != tokens["refresh"]
    # The old refresh token is blacklisted after rotation.
    assert api_client.post("/api/v1/auth/refresh", {"refresh": tokens["refresh"]}).status_code == 401


def test_logout_blacklists_refresh(api_client, otp_code):
    tokens = api_client.post(VERIFY_URL, {"phone": PHONE, "code": otp_code}).data

    response = api_client.post("/api/v1/auth/logout", {"refresh": tokens["refresh"]})

    assert response.status_code == 204
    assert api_client.post("/api/v1/auth/refresh", {"refresh": tokens["refresh"]}).status_code == 401


def test_logout_with_garbage_token(api_client):
    response = api_client.post("/api/v1/auth/logout", {"refresh": "not-a-token"})

    assert response.status_code == 400
