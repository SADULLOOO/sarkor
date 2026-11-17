from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.exceptions import WrongStatus
from core.models import PlatformSettings
from users.models import User

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
