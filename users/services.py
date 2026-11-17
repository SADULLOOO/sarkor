import secrets

from django.core.cache import cache
from django.utils import translation
from django.utils.translation import gettext as _

from core.sms import get_sms_provider

OTP_LENGTH = 6
OTP_TTL = 5 * 60
OTP_REQUEST_LIMIT = 3
OTP_REQUEST_WINDOW = 10 * 60


class OtpRateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Too many OTP requests, retry after {retry_after}s")


def _code_key(phone: str) -> str:
    return f"otp:code:{phone}"


def _requests_key(phone: str) -> str:
    return f"otp:requests:{phone}"


def generate_otp() -> str:
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


def request_otp(phone: str, language: str = "ru") -> None:
    requests_key = _requests_key(phone)
    cache.add(requests_key, 0, OTP_REQUEST_WINDOW)
    if cache.incr(requests_key) > OTP_REQUEST_LIMIT:
        raise OtpRateLimitError(retry_after=cache.ttl(requests_key) or OTP_REQUEST_WINDOW)

    code = generate_otp()
    cache.set(_code_key(phone), code, OTP_TTL)

    with translation.override(language):
        message = _("Your Sarkor code: %(code)s") % {"code": code}
    get_sms_provider().send(phone, message)
