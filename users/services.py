import secrets

from django.core.cache import cache
from django.utils import translation
from django.utils.translation import gettext as _

from core.sms import get_sms_provider

from .models import User

OTP_LENGTH = 6
OTP_TTL = 5 * 60
OTP_REQUEST_LIMIT = 3
OTP_REQUEST_WINDOW = 10 * 60
OTP_MAX_ATTEMPTS = 5
OTP_LOCK_TIME = 15 * 60


class OtpRateLimitError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Too many OTP requests, retry after {retry_after}s")


class OtpInvalidError(Exception):
    pass


def _code_key(phone: str) -> str:
    return f"otp:code:{phone}"


def _requests_key(phone: str) -> str:
    return f"otp:requests:{phone}"


def _attempts_key(phone: str) -> str:
    return f"otp:attempts:{phone}"


def _lock_key(phone: str) -> str:
    return f"otp:lock:{phone}"


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


def verify_otp(phone: str, code: str) -> tuple[User, bool]:
    """Check the code and return (user, created). The user is created on first login."""
    lock_key = _lock_key(phone)
    if cache.get(lock_key):
        raise OtpRateLimitError(retry_after=cache.ttl(lock_key) or OTP_LOCK_TIME)

    expected = cache.get(_code_key(phone))
    if expected is None or not secrets.compare_digest(expected, code):
        _register_failed_attempt(phone)
        raise OtpInvalidError

    cache.delete_many([_code_key(phone), _attempts_key(phone), _requests_key(phone)])

    user = User.objects.filter(phone=phone).first()
    if user:
        return user, False
    return User.objects.create_user(phone), True


def _register_failed_attempt(phone: str) -> None:
    attempts_key = _attempts_key(phone)
    cache.add(attempts_key, 0, OTP_LOCK_TIME)
    if cache.incr(attempts_key) >= OTP_MAX_ATTEMPTS:
        cache.set(_lock_key(phone), True, OTP_LOCK_TIME)
        # The old code must not work after the lock, the user has to request a new one.
        cache.delete_many([_code_key(phone), attempts_key])
