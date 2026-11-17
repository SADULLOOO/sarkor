from django.utils.translation import gettext as _
from rest_framework import serializers

from catalog.models import Category, District
from catalog.serializers import CategorySerializer, DistrictSerializer
from core.validators import validate_image_size

from .models import ExecutorProfile, PortfolioPhoto, User, phone_validator
from .profile import get_completeness


class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(validators=[phone_validator])


class OtpVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(validators=[phone_validator])
    code = serializers.RegexField(r"^\d{6}$")


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AuthUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "name", "language", "is_customer", "is_executor", "trust_level"]


class MeSerializer(serializers.ModelSerializer):
    profile_completeness = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = AuthUserSerializer.Meta.fields + ["date_joined", "profile_completeness"]
        read_only_fields = ["id", "phone", "trust_level", "date_joined"]

    def validate_name(self, value):
        return value.strip()

    def get_profile_completeness(self, user):
        profile = getattr(user, "executor_profile", None)
        if profile is None:
            return None
        percent, missing = get_completeness(profile)
        return {"percent": percent, "missing": missing}


class PortfolioPhotoSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(validators=[validate_image_size])

    class Meta:
        model = PortfolioPhoto
        fields = ["id", "image", "created_at"]


class ExecutorProfileSerializer(serializers.ModelSerializer):
    """The executor's own profile, editable."""

    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.filter(is_active=True), required=False
    )
    districts = serializers.PrimaryKeyRelatedField(many=True, queryset=District.objects.all(), required=False)
    photo = serializers.ImageField(validators=[validate_image_size], required=False, allow_null=True)
    portfolio = PortfolioPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ExecutorProfile
        fields = [
            "categories",
            "districts",
            "photo",
            "about",
            "experience_years",
            "available_now",
            "rating",
            "reviews_count",
            "completed_count",
            "portfolio",
        ]
        read_only_fields = ["rating", "reviews_count", "completed_count"]

    def validate_categories(self, value):
        if len(value) > ExecutorProfile.MAX_CATEGORIES:
            raise serializers.ValidationError(
                _("You can choose up to %(max)s categories.") % {"max": ExecutorProfile.MAX_CATEGORIES}
            )
        return value


class PublicExecutorSerializer(serializers.ModelSerializer):
    """What customers see. No phone here, it opens only after the executor is selected."""

    id = serializers.IntegerField(source="user.id")
    name = serializers.CharField(source="user.name")
    trust_level = serializers.CharField(source="user.trust_level")
    categories = CategorySerializer(many=True)
    districts = DistrictSerializer(many=True)
    portfolio = PortfolioPhotoSerializer(many=True)

    class Meta:
        model = ExecutorProfile
        fields = [
            "id",
            "name",
            "trust_level",
            "photo",
            "about",
            "experience_years",
            "categories",
            "districts",
            "rating",
            "reviews_count",
            "completed_count",
            "portfolio",
        ]
