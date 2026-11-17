import pytest

from conftest import client_for
from tasks.models import Response, Task
from users.models import ExecutorProfile

from .factories import make_task, make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def task():
    return make_task()


@pytest.fixture
def executor():
    user = make_user(is_executor=True)
    ExecutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def response(task, executor):
    return Response.objects.create(task=task, executor=executor, price=100)


def url(task, action):
    return f"/api/v1/tasks/{task.id}/{action}"


def test_select_opens_contacts(task, response, executor):
    result = client_for(task.customer).post(url(task, "select"), {"response": response.id})

    assert result.status_code == 200
    assert result.data["status"] == "assigned"
    assert result.data["executor"]["phone"] == executor.phone
    assert result.data["customer"]["phone"] == task.customer.phone

    executor_view = client_for(executor).get(f"/api/v1/tasks/{task.id}").data
    assert executor_view["customer"]["phone"] == task.customer.phone
    assert executor_view["address"] == task.address


def test_only_customer_selects(task, response, executor):
    assert client_for(executor).post(url(task, "select"), {"response": response.id}).status_code == 403


def test_select_unknown_response(task):
    result = client_for(task.customer).post(url(task, "select"), {"response": 999999})

    assert result.status_code == 400


def test_full_flow(task, response, executor):
    customer_client = client_for(task.customer)
    executor_client = client_for(executor)

    customer_client.post(url(task, "select"), {"response": response.id})
    assert executor_client.post(url(task, "start")).data["status"] == "in_progress"
    assert customer_client.post(url(task, "complete")).data["status"] == "completed"

    executor.executor_profile.refresh_from_db()
    assert executor.executor_profile.completed_count == 1


def test_customer_cannot_start(task, response):
    client = client_for(task.customer)
    client.post(url(task, "select"), {"response": response.id})

    assert client.post(url(task, "start")).status_code == 403


def test_cannot_complete_open_task(task):
    result = client_for(task.customer).post(url(task, "complete"))

    assert result.status_code == 409


def test_cancel(task):
    result = client_for(task.customer).post(url(task, "cancel"))

    assert result.status_code == 200
    task.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    assert task.cancelled_at is not None


def test_cannot_cancel_in_progress(task, response, executor):
    client_for(task.customer).post(url(task, "select"), {"response": response.id})
    client_for(executor).post(url(task, "start"))

    assert client_for(task.customer).post(url(task, "cancel")).status_code == 409


def test_no_show_returns_task_to_search(task, response, executor):
    client = client_for(task.customer)
    client.post(url(task, "select"), {"response": response.id})

    result = client.post(url(task, "no-show"))

    assert result.status_code == 200
    assert result.data["status"] == "open"
    assert result.data["executor"] is None
    response.refresh_from_db()
    assert response.status == Response.Status.NO_SHOW


def test_other_responses_stay_after_no_show(task, response, executor):
    other = make_user(is_executor=True)
    other_response = Response.objects.create(task=task, executor=other, price=120)
    client = client_for(task.customer)
    client.post(url(task, "select"), {"response": response.id})
    client.post(url(task, "no-show"))

    result = client.post(url(task, "select"), {"response": other_response.id})

    assert result.status_code == 200
    assert result.data["executor"]["id"] == other.id
