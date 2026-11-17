from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.exceptions import WrongStatus
from core.models import PlatformSettings
from core.pagination import NewestFirstPagination
from users.permissions import IsExecutor

from . import services
from .models import Response as TaskResponse
from .models import Task
from .serializers import ResponseSerializer, TaskPhotoSerializer, TaskSerializer, TaskWriteSerializer


def tasks_with_details():
    return (
        Task.objects.select_related("category", "district", "customer", "executor")
        .prefetch_related("photos")
        .annotate(responses_count=Count("responses"))
    )


class TaskViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    pagination_class = NewestFirstPagination
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        user = self.request.user
        queryset = tasks_with_details()

        if self.action == "list":
            queryset = queryset.filter(status=Task.Status.OPEN).exclude(customer=user)
            return self._apply_filters(queryset)
        if self.action == "my":
            return queryset.filter(customer=user)
        if self.action == "assigned":
            return queryset.filter(executor=user)

        # A single task: open ones are public, the rest only for participants.
        return queryset.filter(Q(status=Task.Status.OPEN) | Q(customer=user) | Q(executor=user))

    def _apply_filters(self, queryset):
        params = self.request.query_params
        if category := params.get("category"):
            queryset = queryset.filter(category_id=category)
        if district := params.get("district"):
            queryset = queryset.filter(district_id=district)
        if task_type := params.get("type"):
            queryset = queryset.filter(type=task_type)
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return TaskWriteSerializer
        if self.action == "add_photo":
            return TaskPhotoSerializer
        if self.action == "responses":
            return ResponseSerializer
        return TaskSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(customer=request.user)

        if not request.user.is_customer:
            request.user.is_customer = True
            request.user.save(update_fields=["is_customer"])

        return Response(self._read(task), status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        task = self._get_own_open_task()
        serializer = self.get_serializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._read(task))

    @action(detail=False)
    def my(self, request):
        return self.list(request)

    @action(detail=False)
    def assigned(self, request):
        return self.list(request)

    @action(detail=True, methods=["post"], url_path="photos")
    def add_photo(self, request, pk=None):
        task = self._get_own_open_task()
        if task.photos.count() >= PlatformSettings.load().max_task_photos:
            raise ValidationError({"image": [_("Too many photos.")]})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"photos/(?P<photo_id>\d+)")
    def delete_photo(self, request, pk=None, photo_id=None):
        task = self._get_own_open_task()
        photo = get_object_or_404(task.photos, pk=photo_id)
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"])
    def responses(self, request, pk=None):
        task = self.get_object()

        if request.method == "POST":
            if not IsExecutor().has_permission(request, self):
                raise PermissionDenied(IsExecutor.message)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            response = services.create_response(task.pk, request.user, **serializer.validated_data)
            return Response(self.get_serializer(response).data, status=status.HTTP_201_CREATED)

        if task.customer_id == request.user.id:
            verified_only = request.query_params.get("verified_only") == "true"
            queryset = services.responses_for_customer(task, verified_only=verified_only)
        else:
            # Executors see only their own response.
            queryset = task.responses.filter(executor=request.user)

        queryset = queryset.prefetch_related("executor__executor_profile__portfolio")
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["delete"], url_path=r"responses/(?P<response_id>\d+)")
    def withdraw_response(self, request, pk=None, response_id=None):
        task = self.get_object()
        response = get_object_or_404(task.responses, pk=response_id, executor=request.user)
        if response.status != TaskResponse.Status.PENDING or task.status != Task.Status.OPEN:
            raise WrongStatus
        response.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_own_open_task(self):
        task = self.get_object()
        if task.customer_id != self.request.user.id:
            raise PermissionDenied(_("This is not your task."))
        if task.status != Task.Status.OPEN:
            raise WrongStatus(_("The task can't be changed after an executor is selected."))
        return task

    def _read(self, task):
        task = tasks_with_details().get(pk=task.pk)
        return TaskSerializer(task, context=self.get_serializer_context()).data
