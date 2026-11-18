import pytest

from catalog.models import Category

pytestmark = pytest.mark.django_db


def test_districts_are_public(api_client):
    response = api_client.get("/api/v1/districts")

    assert response.status_code == 200
    assert [d["slug"] for d in response.data] == ["sino", "firdavsi", "shohmansur", "somoni"]


def test_categories_in_russian_by_default(api_client):
    response = api_client.get("/api/v1/categories")

    delivery = next(c for c in response.data if c["slug"] == "delivery")
    assert delivery["name"] == "Доставка"


def test_categories_in_tajik(api_client):
    response = api_client.get("/api/v1/categories", HTTP_ACCEPT_LANGUAGE="tg")

    delivery = next(c for c in response.data if c["slug"] == "delivery")
    assert delivery["name"] == "Расонидан"


def test_inactive_categories_are_hidden(api_client):
    Category.objects.filter(slug="tutoring").update(is_active=False)

    response = api_client.get("/api/v1/categories")

    assert "tutoring" not in [c["slug"] for c in response.data]
