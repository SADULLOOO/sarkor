from rest_framework import serializers

from .models import Category, District


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name", "icon", "parent"]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "slug", "name"]
