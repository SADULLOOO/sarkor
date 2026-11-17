from rest_framework import serializers

from .models import User, phone_validator


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
    class Meta:
        model = User
        fields = AuthUserSerializer.Meta.fields + ["date_joined"]
        read_only_fields = ["id", "phone", "trust_level", "date_joined"]

    def validate_name(self, value):
        return value.strip()
