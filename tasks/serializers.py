from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from catalog.models import Category, District
from catalog.serializers import CategorySerializer, DistrictSerializer
from core.validators import validate_image_size

from .models import Task, TaskPhoto


class TaskPhotoSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(validators=[validate_image_size])

    class Meta:
        model = TaskPhoto
        fields = ["id", "image"]


class TaskUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    trust_level = serializers.CharField()


class TaskSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    district = DistrictSerializer()
    photos = TaskPhotoSerializer(many=True)
    customer = TaskUserSerializer()
    executor = TaskUserSerializer(allow_null=True)
    responses_count = serializers.IntegerField(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "type",
            "status",
            "category",
            "description",
            "photos",
            "voice",
            "district",
            "address",
            "latitude",
            "longitude",
            "timing",
            "scheduled_at",
            "budget",
            "customer",
            "executor",
            "responses_count",
            "is_mine",
            "created_at",
        ]

    def get_is_mine(self, task):
        return task.customer_id == self.context["request"].user.id

    def to_representation(self, task):
        data = super().to_representation(task)
        user = self.context["request"].user

        # Exact address and phones are shown only to the customer and the selected executor.
        if task.is_participant(user):
            if task.executor_id:
                data["customer"]["phone"] = task.customer.phone
                data["executor"]["phone"] = task.executor.phone
        else:
            for field in ("address", "latitude", "longitude"):
                data[field] = None
        return data


class TaskWriteSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(is_active=True))
    district = serializers.PrimaryKeyRelatedField(queryset=District.objects.all())

    class Meta:
        model = Task
        fields = [
            "category",
            "description",
            "voice",
            "district",
            "address",
            "latitude",
            "longitude",
            "timing",
            "scheduled_at",
            "budget",
        ]

    def validate_budget(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(_("Budget must be greater than zero."))
        return value

    def validate(self, attrs):
        timing = attrs.get("timing", getattr(self.instance, "timing", Task.Timing.TODAY))
        scheduled_at = attrs.get("scheduled_at", getattr(self.instance, "scheduled_at", None))

        if timing == Task.Timing.SCHEDULED:
            if not scheduled_at:
                raise serializers.ValidationError({"scheduled_at": [_("Choose date and time.")]})
            if scheduled_at <= timezone.now():
                raise serializers.ValidationError({"scheduled_at": [_("Date must be in the future.")]})
        else:
            attrs["scheduled_at"] = None

        attrs["type"] = Task.Type.URGENT if timing == Task.Timing.URGENT else Task.Type.ONE_OFF
        return attrs
