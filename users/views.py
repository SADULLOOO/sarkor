from django.utils.translation import gettext as _
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import OtpRequestSerializer


class OtpRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            services.request_otp(serializer.validated_data["phone"], language=request.LANGUAGE_CODE)
        except services.OtpRateLimitError as exc:
            raise Throttled(wait=exc.retry_after) from exc

        return Response({"detail": _("The code has been sent.")})
