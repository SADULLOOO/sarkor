import logging

import pytest
from django.core.cache import cache

from users.services import OTP_REQUEST_LIMIT, generate_otp

URL = "/api/v1/auth/otp/request"
PHONE = "+992901234567"


def test_generate_otp_is_six_digits():
    for _ in range(50):
        code = generate_otp()
        assert len(code) == 6
        assert code.isdigit()


def test_request_sends_code(api_client, caplog):
    with caplog.at_level(logging.INFO):
        response = api_client.post(URL, {"phone": PHONE})

    assert response.status_code == 200
    code = cache.get(f"otp:code:{PHONE}")
    assert code in caplog.text
    assert "code" not in response.data


@pytest.mark.parametrize("phone", ["992901234567", "+99290", "", "+992abcdefghi"])
def test_invalid_phone(api_client, phone):
    response = api_client.post(URL, {"phone": phone})

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert "phone" in response.data["fields"]


def test_rate_limit(api_client):
    for _ in range(OTP_REQUEST_LIMIT):
        assert api_client.post(URL, {"phone": PHONE}).status_code == 200

    response = api_client.post(URL, {"phone": PHONE})

    assert response.status_code == 429
    assert response.data["code"] == "throttled"


def test_rate_limit_is_per_phone(api_client):
    for _ in range(OTP_REQUEST_LIMIT):
        api_client.post(URL, {"phone": PHONE})

    assert api_client.post(URL, {"phone": "+992907654321"}).status_code == 200
