import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from users.models import User

pytestmark = pytest.mark.django_db


def test_create_user_has_no_usable_password():
    user = User.objects.create_user("+992901234567")

    assert not user.has_usable_password()
    assert user.trust_level == User.TrustLevel.NEWBIE
    assert not user.is_staff


def test_create_superuser():
    user = User.objects.create_superuser("+992901234567", "strong-pass-123")

    assert user.is_staff
    assert user.is_superuser
    assert user.check_password("strong-pass-123")


@pytest.mark.parametrize("phone", ["992901234567", "+99290123", "+79001234567", "+992 90 123 45 67"])
def test_phone_validation(phone):
    user = User(phone=phone)

    with pytest.raises(ValidationError):
        user.full_clean()


def test_staff_groups_exist():
    moderator = Group.objects.get(name="Moderator")
    admin = Group.objects.get(name="Admin")

    assert set(moderator.permissions.values_list("codename", flat=True)) == {"view_user", "change_user"}
    assert "delete_user" in admin.permissions.values_list("codename", flat=True)


def test_admin_can_create_user(admin_client):
    response = admin_client.post(
        "/admin/users/user/add/",
        {"phone": "+992901112233", "password1": "Very-strong-123", "password2": "Very-strong-123"},
    )

    assert response.status_code == 302
    assert User.objects.get(phone="+992901112233").check_password("Very-strong-123")
