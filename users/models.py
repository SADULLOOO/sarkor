from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

phone_validator = RegexValidator(r"^\+992\d{9}$", _("Enter a valid phone number: +992XXXXXXXXX"))

class UserManager(BaseUserManager):
    def create_user(self, phone, **extra_fields):
        if not phone:
            raise ValueError('Phone is required!')
        user = self.model(phone=phone, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    


class User(AbstractBaseUser, PermissionsMixin):
    class Language(models.TextChoices):
        TG = "tg", "Тоҷикӣ"
        RU = "ru", "Русский"

    class TrustLevel(models.TextChoices):
        NEWBIE = "newbie", _("Newbie")
        PROFILE_FILLED = "profile_filled", _("Profile Filled")
        VERIFIED = "verified",_("Verified")
        RELIABLE = "reliable", _("Reliable")
        CAUTION = "caution", ("Caution")

    phone = models.CharField(_("phone"), max_length=13, unique=True, validators=[phone_validator])
    name = models.CharField(_("name"), max_length=100, blank=True)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.RU)

    is_customer = models.BooleanField(default=False)
    is_executor = models.BooleanField(default=False)
    trust_level = models.CharField(max_length=20, choices=TrustLevel.choices,
                                    default=TrustLevel.NEWBIE)
    is_blocked = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=TrustLevel)

    objects = UserManager()

    USERNAME_FIELD = "phone"

    def __str__(self):
        return self.name or self.phone







# Create your models here.
