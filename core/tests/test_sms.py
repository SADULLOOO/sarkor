import logging

from core.sms import ConsoleSmsProvider, get_sms_provider


def test_console_provider_logs_phone_and_message(caplog):
    with caplog.at_level(logging.INFO):
        ConsoleSmsProvider().send("+992901234567", "Code: 123456")

    assert "+992901234567" in caplog.text
    assert "Code: 123456" in caplog.text


def test_get_sms_provider_uses_settings(settings):
    settings.SMS_PROVIDER = "core.sms.ConsoleSmsProvider"

    assert isinstance(get_sms_provider(), ConsoleSmsProvider)
