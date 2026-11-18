from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from conftest import client_for
from tasks.models import Task
from users.models import ExecutorProfile, User

from .factories import make_task, make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def executor():
    user = make_user(is_executor=True)
    ExecutorProfile.objects.create(user=user)
    return user


def completed_task(executor, **kwargs):
    kwargs.setdefault("completed_at", timezone.now())
    return make_task(executor=executor, status=Task.Status.COMPLETED, **kwargs)


def review_url(task):
    return f"/api/v1/tasks/{task.id}/reviews"


def test_customer_reviews_executor(executor):
    task = completed_task(executor)

    response = client_for(task.customer).post(review_url(task), {"rating": 5, "text": "Great"})

    assert response.status_code == 201
    executor.executor_profile.refresh_from_db()
    assert executor.executor_profile.rating == Decimal("5.00")
    assert executor.executor_profile.reviews_count == 1


def test_rating_is_average(executor):
    for rating in (5, 4, 4):
        task = completed_task(executor)
        client_for(task.customer).post(review_url(task), {"rating": rating})

    executor.executor_profile.refresh_from_db()
    assert executor.executor_profile.rating == Decimal("4.33")


def test_executor_review_of_customer_does_not_touch_executor_rating(executor):
    task = completed_task(executor)

    client_for(executor).post(review_url(task), {"rating": 1})

    executor.executor_profile.refresh_from_db()
    assert executor.executor_profile.reviews_count == 0
    assert task.reviews.get().target == task.customer


def test_both_reviews_close_the_task(executor):
    task = completed_task(executor)

    client_for(task.customer).post(review_url(task), {"rating": 5})
    client_for(executor).post(review_url(task), {"rating": 5})

    task.refresh_from_db()
    assert task.status == Task.Status.CLOSED


def test_only_after_completion(executor):
    task = make_task(executor=executor, status=Task.Status.IN_PROGRESS)

    assert client_for(task.customer).post(review_url(task), {"rating": 5}).status_code == 409


def test_one_review_per_side(executor):
    task = completed_task(executor)
    client = client_for(task.customer)
    client.post(review_url(task), {"rating": 5})

    assert client.post(review_url(task), {"rating": 4}).status_code == 400


def test_rating_range(executor):
    task = completed_task(executor)

    assert client_for(task.customer).post(review_url(task), {"rating": 6}).status_code == 400


def test_strangers_cannot_review(executor):
    task = completed_task(executor)

    # A completed task isn't visible to other users at all.
    assert client_for(make_user()).post(review_url(task), {"rating": 1}).status_code == 404


def test_review_period_is_over(executor):
    task = completed_task(executor, completed_at=timezone.now() - timedelta(days=20))

    assert client_for(task.customer).post(review_url(task), {"rating": 5}).status_code == 409


def test_verified_executor_becomes_reliable(executor):
    executor.trust_level = User.TrustLevel.VERIFIED
    executor.save()
    ExecutorProfile.objects.filter(user=executor).update(completed_count=10)

    task = completed_task(executor)
    client_for(task.customer).post(review_url(task), {"rating": 5})

    executor.refresh_from_db()
    assert executor.trust_level == User.TrustLevel.RELIABLE


def test_public_executor_reviews(executor):
    task = completed_task(executor)
    client_for(task.customer).post(review_url(task), {"rating": 5, "text": "Fast"})

    response = client_for(make_user()).get(f"/api/v1/executors/{executor.id}/reviews")

    assert response.status_code == 200
    assert [r["text"] for r in response.data["results"]] == ["Fast"]


def test_close_stale_tasks_command(executor):
    old = completed_task(executor, completed_at=timezone.now() - timedelta(days=15))
    fresh = completed_task(executor)

    call_command("close_stale_tasks")

    old.refresh_from_db()
    fresh.refresh_from_db()
    assert old.status == Task.Status.CLOSED
    assert fresh.status == Task.Status.COMPLETED
