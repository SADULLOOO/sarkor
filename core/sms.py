import logging 
from abc import ABC, abstractmethod

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

class SmsProvider(ABC):
    @abstractmethod
    def send(self, phone: str, message: str) -> None:
        pass



class ConsoleSmsProvider(SmsProvider):
    def send(self, phone: str, message: str) -> None:
        logger.info("SMS to %s: %s", phone, message)

def get_sms_provider() -> SmsProvider:
    provider_class = import_string(settings.SMS_PROVIDER)
    return provider_class()
    

