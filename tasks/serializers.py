from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from catalog.models import Category, District
from catalog.serializers import CategorySerializer, DistrictSerializer
from core.validators import validate_image_size
from users.models import User

from .models import Response, Task, TaskPhoto


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


class ResponseExecutorSerializer(serializers.Serializer):
    """Executor card inside a response: trust level and what is missing in the profile."""

    def _url(self, file):
        request = self.context.get("request")
        return request.build_absolute_uri(file.url) if request else file.url

    def to_representation(self, user):
        profile = getattr(user, "executor_profile", None)
        missing = []
        if not profile or not profile.photo:
            missing.append("photo")
        if not profile or not profile.reviews_count:
            missing.append("reviews")
        if user.trust_level not in (User.TrustLevel.VERIFIED, User.TrustLevel.RELIABLE):
            missing.append("verification")

        data = {
            "id": user.id,
            "name": user.name,
            "trust_level": user.trust_level,
            "photo": self._url(profile.photo) if profile and profile.photo else None,
            "rating": str(profile.rating) if profile else "0.00",
            "reviews_count": profile.reviews_count if profile else 0,
            "completed_count": profile.completed_count if profile else 0,
            "missing": missing,
        }
        # Portfolio is shown only for a filled profile and higher.
        if profile and user.trust_level != User.TrustLevel.NEWBIE:
            data["portfolio"] = [self._url(photo.image) for photo in profile.portfolio.all()[:6]]
        return data


class ResponseSerializer(serializers.ModelSerializer):
    executor = ResponseExecutorSerializer(read_only=True)

    class Meta:
        model = Response
        fields = ["id", "executor", "price", "comment", "status", "created_at"]
        read_only_fields = ["status"]
