from datetime import timedelta

import pytest
from django.utils import timezone

from catalog.models import Category, District
from conftest import client_for, make_image
from tasks.models import Task

from .factories import make_task, make_user

pytestmark = pytest.mark.django_db

URL = "/api/v1/tasks"


@pytest.fixture
def customer():
    return make_user()


@pytest.fixture
def customer_client(customer):
    return client_for(customer)


def task_payload(**overrides):
    payload = {
        "category": Category.objects.get(slug="plumbing").id,
        "district": District.objects.get(slug="sino").id,
        "description": "Kitchen tap is leaking",
        "address": "Rudaki 10",
        "timing": "today",
    }
    payload.update(overrides)
    return payload


def test_create_task(customer_client, customer):
    response = customer_client.post(URL, task_payload(), format="json")

    assert response.status_code == 201
    assert response.data["status"] == "open"
    assert response.data["type"] == "one_off"
    assert response.data["budget"] is None
    customer.refresh_from_db()
    assert customer.is_customer


def test_urgent_timing_makes_urgent_task(customer_client):
    response = customer_client.post(URL, task_payload(timing="urgent"), format="json")

    assert response.data["type"] == "urgent"


def test_scheduled_needs_future_date(customer_client):
    past = timezone.now() - timedelta(hours=1)

    assert customer_client.post(URL, task_payload(timing="scheduled"), format="json").status_code == 400
    response = customer_client.post(URL, task_payload(timing="scheduled", scheduled_at=past), format="json")
    assert response.status_code == 400
    assert "scheduled_at" in response.data["fields"]


def test_budget_must_be_positive(customer_client):
    response = customer_client.post(URL, task_payload(budget="-10"), format="json")

    assert response.status_code == 400


def test_feed_shows_only_open_tasks_of_others(customer_client, customer):
    other_open = make_task()
    make_task(status=Task.Status.CANCELLED)
    make_task(customer=customer)

    response = customer_client.get(URL)

    assert [t["id"] for t in response.data["results"]] == [other_open.id]


def test_feed_filters(customer_client):
    plumbing = make_task()
    make_task(category=Category.objects.get(slug="cleaning"))
    make_task(district=District.objects.get(slug="somoni"))

    response = customer_client.get(URL, {"category": plumbing.category_id, "district": plumbing.district_id})

    assert [t["id"] for t in response.data["results"]] == [plumbing.id]


def test_address_hidden_from_strangers(customer_client):
    task = make_task()

    response = customer_client.get(f"{URL}/{task.id}")

    assert response.status_code == 200
    assert response.data["address"] is None
    assert "phone" not in response.data["customer"]


def test_my_tasks(customer_client, customer):
    mine = make_task(customer=customer, status=Task.Status.CANCELLED)
    make_task()

    response = customer_client.get(f"{URL}/my")

    assert [t["id"] for t in response.data["results"]] == [mine.id]
    assert response.data["results"][0]["address"] == "Rudaki 10, apt 5"


def test_closed_task_of_someone_else_is_not_found(customer_client):
    task = make_task(status=Task.Status.ASSIGNED)

    assert customer_client.get(f"{URL}/{task.id}").status_code == 404


def test_customer_edits_open_task(customer_client, customer):
    task = make_task(customer=customer)

    response = customer_client.patch(f"{URL}/{task.id}", {"budget": "300"}, format="json")

    assert response.status_code == 200
    assert response.data["budget"] == "300.00"


def test_cannot_edit_foreign_task(customer_client):
    task = make_task()

    response = customer_client.patch(f"{URL}/{task.id}", {"budget": "300"}, format="json")

    assert response.status_code == 403


def test_cannot_edit_after_assignment(customer_client, customer):
    task = make_task(customer=customer, status=Task.Status.ASSIGNED)

    response = customer_client.patch(f"{URL}/{task.id}", {"budget": "300"}, format="json")

    assert response.status_code == 409
    assert response.data["code"] == "wrong_status"


def test_photos(customer_client, customer):
    task = make_task(customer=customer)

    response = customer_client.post(f"{URL}/{task.id}/photos", {"image": make_image()})
    assert response.status_code == 201

    photo_id = response.data["id"]
    assert customer_client.delete(f"{URL}/{task.id}/photos/{photo_id}").status_code == 204
    assert not task.photos.exists()


def test_photo_limit(customer_client, customer):
    from core.models import PlatformSettings

    settings = PlatformSettings.load()
    settings.max_task_photos = 1
    settings.save()
    task = make_task(customer=customer)

    customer_client.post(f"{URL}/{task.id}/photos", {"image": make_image()})
    response = customer_client.post(f"{URL}/{task.id}/photos", {"image": make_image()})

    assert response.status_code == 400
