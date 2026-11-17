from django.db import transaction
from django.db.models import Case, F, IntegerField, Value, When
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.exceptions import WrongStatus
from core.models import PlatformSettings
from users.models import ExecutorProfile, User

from .models import Response, Task

# Who is allowed to respond to tasks with a big budget.
TRUSTED_LEVELS = {User.TrustLevel.VERIFIED, User.TrustLevel.RELIABLE}


@transaction.atomic
def create_response(task_id: int, executor: User, price, comment: str = "") -> Response:
    # Lock the task row so two executors can't both pass the "max responses" check.
    task = Task.objects.select_for_update().get(pk=task_id)
    platform = PlatformSettings.load()

    if task.status != Task.Status.OPEN:
        raise WrongStatus(_("The task is not accepting responses."))
    if task.customer_id == executor.id:
        raise PermissionDenied(_("You can't respond to your own task."))
    if (
        task.budget
        and task.budget > platform.newbie_budget_limit
        and executor.trust_level not in TRUSTED_LEVELS
    ):
        raise PermissionDenied(_("Only verified executors can respond to this task."))
    if task.responses.filter(executor=executor).exists():
        raise ValidationError(_("You have already responded to this task."))
    if task.responses.count() >= platform.max_responses_per_task:
        raise WrongStatus(_("The task already has enough responses."))

    return Response.objects.create(task=task, executor=executor, price=price, comment=comment)


def responses_for_customer(task: Task, verified_only: bool = False):
    """Reliable first, then verified, then everyone else. Inside a group by rating."""
    queryset = task.responses.select_related("executor", "executor__executor_profile").annotate(
        trust_rank=Case(
            When(executor__trust_level=User.TrustLevel.RELIABLE, then=Value(0)),
            When(executor__trust_level=User.TrustLevel.VERIFIED, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    )
    if verified_only:
        queryset = queryset.filter(executor__trust_level__in=TRUSTED_LEVELS)
    return queryset.order_by("trust_rank", "-executor__executor_profile__rating", "created_at")


def _lock_task(task_id: int) -> Task:
    return Task.objects.select_for_update().get(pk=task_id)


def _check_status(task: Task, *allowed: str) -> None:
    if task.status not in allowed:
        raise WrongStatus


@transaction.atomic
def select_executor(task_id: int, customer: User, response_id: int) -> Task:
    task = _lock_task(task_id)
    if task.customer_id != customer.id:
        raise PermissionDenied
    _check_status(task, Task.Status.OPEN)

    response = task.responses.filter(pk=response_id, status=Response.Status.PENDING).first()
    if response is None:
        raise ValidationError({"response": [_("Response not found.")]})

    response.status = Response.Status.ACCEPTED
    response.save(update_fields=["status"])

    task.executor = response.executor
    task.status = Task.Status.ASSIGNED
    task.assigned_at = timezone.now()
    task.save(update_fields=["executor", "status", "assigned_at", "updated_at"])
    return task


@transaction.atomic
def start_task(task_id: int, executor: User) -> Task:
    task = _lock_task(task_id)
    if task.executor_id != executor.id:
        raise PermissionDenied
    _check_status(task, Task.Status.ASSIGNED)

    task.status = Task.Status.IN_PROGRESS
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_at", "updated_at"])
    return task


@transaction.atomic
def complete_task(task_id: int, user: User) -> Task:
    task = _lock_task(task_id)
    if not task.is_participant(user):
        raise PermissionDenied
    _check_status(task, Task.Status.ASSIGNED, Task.Status.IN_PROGRESS)

    task.status = Task.Status.COMPLETED
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_at", "updated_at"])

    ExecutorProfile.objects.filter(user_id=task.executor_id).update(completed_count=F("completed_count") + 1)
    return task


@transaction.atomic
def cancel_task(task_id: int, customer: User) -> Task:
    task = _lock_task(task_id)
    if task.customer_id != customer.id:
        raise PermissionDenied
    _check_status(task, Task.Status.OPEN, Task.Status.ASSIGNED)

    task.status = Task.Status.CANCELLED
    task.cancelled_at = timezone.now()
    task.save(update_fields=["status", "cancelled_at", "updated_at"])
    # TODO: risk signal for too many cancellations once antifraud (M8) is in.
    return task


@transaction.atomic
def report_no_show(task_id: int, customer: User) -> Task:
    """The selected executor didn't come: put the task back to search."""
    task = _lock_task(task_id)
    if task.customer_id != customer.id:
        raise PermissionDenied
    _check_status(task, Task.Status.ASSIGNED)

    task.responses.filter(executor_id=task.executor_id).update(status=Response.Status.NO_SHOW)
    task.executor = None
    task.status = Task.Status.OPEN
    task.assigned_at = None
    task.save(update_fields=["executor", "status", "assigned_at", "updated_at"])
    return task
