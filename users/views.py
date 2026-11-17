from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext as _
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .serializers import (
    AuthUserSerializer,
    LogoutSerializer,
    MeSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
)


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


class OtpVerifyView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, created = services.verify_otp(**serializer.validated_data)
        except services.OtpRateLimitError as exc:
            raise Throttled(wait=exc.retry_after) from exc
        except services.OtpInvalidError as exc:
            raise ValidationError({"code": [_("Wrong or expired code.")]}) from exc

        if user.is_blocked or not user.is_active:
            raise PermissionDenied(_("Your account is blocked."))

        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "is_new": created,
                "user": AuthUserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": [_("Invalid or expired token.")]}) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    http_method_names = ["get", "patch"]

    def get_object(self):
        return self.request.user
