import pytest

pytestmark = pytest.mark.django_db

URL = "/api/v1/me"


def test_requires_auth(api_client):
    response = api_client.get(URL)

    assert response.status_code == 401
    assert response.data["code"] == "not_authenticated"


def test_get_me(auth_client, user):
    response = auth_client.get(URL)

    assert response.status_code == 200
    assert response.data["phone"] == user.phone
    assert response.data["trust_level"] == "newbie"


def test_update_profile(auth_client, user):
    response = auth_client.patch(URL, {"name": "  Ali  ", "language": "tg", "is_executor": True})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.name == "Ali"
    assert user.language == "tg"
    assert user.is_executor


def test_cannot_change_phone_or_trust_level(auth_client, user):
    auth_client.patch(URL, {"phone": "+992900000000", "trust_level": "reliable"})

    user.refresh_from_db()
    assert user.phone == "+992901234567"
    assert user.trust_level == "newbie"


def test_put_not_allowed(auth_client):
    assert auth_client.put(URL, {"name": "Ali"}).status_code == 405


def test_blocked_user_is_rejected_with_valid_token(auth_client, user):
    user.is_blocked = True
    user.save()

    response = auth_client.get(URL)

    assert response.status_code == 403
