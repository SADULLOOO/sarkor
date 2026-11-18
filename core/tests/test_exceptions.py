from rest_framework import serializers
from rest_framework.exceptions import NotFound

from core.exceptions import api_exception_handler


class DummySerializer(serializers.Serializer):
    phone = serializers.CharField()


def test_validation_error_format():
    serializer = DummySerializer(data={})
    try:
        serializer.is_valid(raise_exception=True)
    except serializers.ValidationError as exc:
        response = api_exception_handler(exc, {})

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "phone" in response.data["fields"]


def test_api_exception_format():
    response = api_exception_handler(NotFound(), {})

    assert response.status_code == 404
    assert response.data["code"] == "not_found"
    assert response.data["fields"] == {}
