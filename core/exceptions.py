from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class WrongStatus(APIException):
    """The object exists, but the action is not allowed in its current status."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = gettext_lazy("This action is not available now.")
    default_code = "wrong_status"


def api_exception_handler(exc, context):
    """Wrap DRF errors into one shape: {code, message, fields}."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        fields = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
        response.data = {
            "code": "validation_error",
            "message": _("Please check the entered data."),
            "fields": fields,
        }
        return response

    detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
    response.data = {
        "code": getattr(detail, "code", "error"),
        "message": str(detail),
        "fields": {},
    }
    return response
