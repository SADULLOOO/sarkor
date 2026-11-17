from rest_framework import serializers

from .models import phone_validator


class OtpRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(validators=[phone_validator])
