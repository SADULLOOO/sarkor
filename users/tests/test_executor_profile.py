import pytest

from catalog.models import Category, District
from conftest import client_for, make_image
from users.models import ExecutorProfile, User

pytestmark = pytest.mark.django_db

URL = "/api/v1/me/executor-profile"
PORTFOLIO_URL = "/api/v1/me/executor-profile/portfolio"


@pytest.fixture
def executor():
    return User.objects.create_user("+992907777777", name="Ali", is_executor=True)


@pytest.fixture
def executor_client(executor):
    return client_for(executor)


def test_only_executors(auth_client):
    assert auth_client.get(URL).status_code == 403


def test_profile_is_created_on_first_get(executor_client, executor):
    response = executor_client.get(URL)

    assert response.status_code == 200
    assert ExecutorProfile.objects.filter(user=executor).exists()


def test_update_categories_and_districts(executor_client, executor):
    categories = list(Category.objects.values_list("id", flat=True)[:3])
    district = District.objects.get(slug="sino")

    response = executor_client.patch(
        URL, {"categories": categories, "districts": [district.id]}, format="json"
    )

    assert response.status_code == 200
    assert sorted(response.data["categories"]) == sorted(categories)


def test_max_five_categories(executor_client):
    categories = list(Category.objects.values_list("id", flat=True)[:6])

    response = executor_client.patch(URL, {"categories": categories}, format="json")

    assert response.status_code == 400
    assert "categories" in response.data["fields"]


def test_rating_is_read_only(executor_client, executor):
    executor_client.patch(URL, {"rating": "5.00", "completed_count": 100}, format="json")

    profile = ExecutorProfile.objects.get(user=executor)
    assert profile.rating == 0
    assert profile.completed_count == 0


def test_filled_profile_raises_trust_level(executor_client, executor):
    executor_client.post(PORTFOLIO_URL, {"image": make_image()}, format="multipart")
    executor_client.patch(
        URL,
        {
            "photo": make_image(),
            "about": "Plumber, 10 years",
            "categories": [Category.objects.get(slug="plumbing").id],
            "districts": [District.objects.get(slug="sino").id],
        },
        format="multipart",
    )

    executor.refresh_from_db()
    assert executor.trust_level == User.TrustLevel.PROFILE_FILLED

    me = executor_client.get("/api/v1/me").data
    assert me["profile_completeness"] == {"percent": 100, "missing": []}


def test_emptied_profile_goes_back_to_newbie(executor_client, executor):
    executor.trust_level = User.TrustLevel.PROFILE_FILLED
    executor.save()
    ExecutorProfile.objects.create(user=executor)

    executor_client.patch(URL, {"about": ""}, format="json")

    executor.refresh_from_db()
    assert executor.trust_level == User.TrustLevel.NEWBIE


def test_verified_level_is_not_touched(executor_client, executor):
    executor.trust_level = User.TrustLevel.VERIFIED
    executor.save()

    executor_client.patch(URL, {"about": ""}, format="json")

    executor.refresh_from_db()
    assert executor.trust_level == User.TrustLevel.VERIFIED


def test_portfolio_limit(executor_client, executor, monkeypatch):
    monkeypatch.setattr(ExecutorProfile, "MAX_PORTFOLIO_PHOTOS", 2)
    for _ in range(2):
        assert executor_client.post(PORTFOLIO_URL, {"image": make_image()}).status_code == 201

    response = executor_client.post(PORTFOLIO_URL, {"image": make_image()})

    assert response.status_code == 400


def test_not_an_image_is_rejected(executor_client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    fake = SimpleUploadedFile("photo.png", b"not an image", content_type="image/png")

    response = executor_client.post(PORTFOLIO_URL, {"image": fake})

    assert response.status_code == 400


def test_cannot_delete_someone_elses_photo(executor_client):
    other = User.objects.create_user("+992908888888", is_executor=True)
    photo = ExecutorProfile.objects.create(user=other).portfolio.create(image=make_image())

    response = executor_client.delete(f"{PORTFOLIO_URL}/{photo.id}")

    assert response.status_code == 404


def test_public_profile_hides_phone(auth_client, executor):
    ExecutorProfile.objects.create(user=executor, about="Plumber")

    response = auth_client.get(f"/api/v1/executors/{executor.id}")

    assert response.status_code == 200
    assert response.data["name"] == "Ali"
    assert "phone" not in response.data


def test_blocked_executor_is_hidden(auth_client, executor):
    ExecutorProfile.objects.create(user=executor)
    executor.is_blocked = True
    executor.save()

    assert auth_client.get(f"/api/v1/executors/{executor.id}").status_code == 404
