from decimal import Decimal

import pytest

from conftest import client_for
from core.models import PlatformSettings
from tasks.models import Task
from users.models import ExecutorProfile, User

from .factories import make_task, make_user

pytestmark = pytest.mark.django_db


def make_executor(trust_level=User.TrustLevel.NEWBIE, rating="0"):
    user = make_user(is_executor=True, trust_level=trust_level)
    ExecutorProfile.objects.create(user=user, rating=Decimal(rating))
    return user


def responses_url(task):
    return f"/api/v1/tasks/{task.id}/responses"


def test_executor_responds_with_price():
    task = make_task()
    executor = make_executor()

    response = client_for(executor).post(responses_url(task), {"price": "150", "comment": "Can come at 5"})

    assert response.status_code == 201
    assert response.data["price"] == "150.00"
    assert response.data["executor"]["missing"] == ["photo", "reviews", "verification"]


def test_price_is_required():
    task = make_task()

    response = client_for(make_executor()).post(responses_url(task), {"comment": "hi"})

    assert response.status_code == 400
    assert "price" in response.data["fields"]


def test_only_executors_can_respond():
    task = make_task()

    response = client_for(make_user()).post(responses_url(task), {"price": "100"})

    assert response.status_code == 403


def test_cannot_respond_twice():
    task = make_task()
    client = client_for(make_executor())
    client.post(responses_url(task), {"price": "100"})

    assert client.post(responses_url(task), {"price": "90"}).status_code == 400


def test_cannot_respond_to_own_task():
    executor = make_executor()
    task = make_task(customer=executor)

    assert client_for(executor).post(responses_url(task), {"price": "100"}).status_code == 403


def test_newbie_cannot_respond_to_big_budget():
    task = make_task(budget=Decimal("800"))

    newbie = client_for(make_executor()).post(responses_url(task), {"price": "800"})
    verified = client_for(make_executor(User.TrustLevel.VERIFIED)).post(responses_url(task), {"price": "800"})

    assert newbie.status_code == 403
    assert verified.status_code == 201


def test_responses_limit():
    settings = PlatformSettings.load()
    settings.max_responses_per_task = 2
    settings.save()
    task = make_task()

    for _ in range(2):
        client_for(make_executor()).post(responses_url(task), {"price": "100"})
    response = client_for(make_executor()).post(responses_url(task), {"price": "100"})

    assert response.status_code == 409


def test_no_responses_to_assigned_task():
    task = make_task(status=Task.Status.ASSIGNED)

    response = client_for(make_executor()).post(responses_url(task), {"price": "100"})

    # Not open, so the executor doesn't see it at all.
    assert response.status_code == 404


def test_customer_sees_responses_sorted_by_trust():
    task = make_task()
    newbie = make_executor(rating="5")
    reliable = make_executor(User.TrustLevel.RELIABLE, rating="4.6")
    verified_good = make_executor(User.TrustLevel.VERIFIED, rating="4.9")
    verified_bad = make_executor(User.TrustLevel.VERIFIED, rating="3.0")
    for executor in (newbie, verified_bad, verified_good, reliable):
        client_for(executor).post(responses_url(task), {"price": "100"})

    response = client_for(task.customer).get(responses_url(task))

    ids = [r["executor"]["id"] for r in response.data]
    assert ids == [reliable.id, verified_good.id, verified_bad.id, newbie.id]


def test_verified_only_filter():
    task = make_task()
    newbie = make_executor()
    verified = make_executor(User.TrustLevel.VERIFIED)
    for executor in (newbie, verified):
        client_for(executor).post(responses_url(task), {"price": "100"})

    response = client_for(task.customer).get(responses_url(task), {"verified_only": "true"})

    assert [r["executor"]["id"] for r in response.data] == [verified.id]


def test_executor_sees_only_own_response():
    task = make_task()
    me = make_executor()
    client_for(make_executor()).post(responses_url(task), {"price": "100"})
    client_for(me).post(responses_url(task), {"price": "120"})

    response = client_for(me).get(responses_url(task))

    assert [r["executor"]["id"] for r in response.data] == [me.id]


def test_withdraw_response():
    task = make_task()
    executor = make_executor()
    client = client_for(executor)
    response_id = client.post(responses_url(task), {"price": "100"}).data["id"]

    assert client_for(make_executor()).delete(f"{responses_url(task)}/{response_id}").status_code == 404
    assert client.delete(f"{responses_url(task)}/{response_id}").status_code == 204
    assert not task.responses.exists()
