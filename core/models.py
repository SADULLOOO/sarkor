from decimal import Decimal

from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _


class PlatformSettings(models.Model):
    """Thresholds the admin can change without a release. There is only one row."""

    CACHE_KEY = "platform-settings"

    newbie_budget_limit = models.DecimalField(
        _("max task budget for newbies"), max_digits=10, decimal_places=2, default=Decimal("500")
    )
    valuable_cargo_limit = models.DecimalField(
        _("valuable cargo from"), max_digits=10, decimal_places=2, default=Decimal("500")
    )
    max_responses_per_task = models.PositiveSmallIntegerField(_("max responses per task"), default=15)
    max_task_photos = models.PositiveSmallIntegerField(_("max photos per task"), default=5)
    cancellations_limit = models.PositiveSmallIntegerField(
        _("cancellations in 30 days before a warning"), default=3
    )
    review_days = models.PositiveSmallIntegerField(_("days to leave a review"), default=14)

    class Meta:
        verbose_name = _("platform settings")
        verbose_name_plural = _("platform settings")

    def __str__(self):
        return str(_("Platform settings"))

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    @classmethod
    def load(cls):
        obj = cache.get(cls.CACHE_KEY)
        if obj is None:
            obj, _created = cls.objects.get_or_create(pk=1)
            cache.set(cls.CACHE_KEY, obj, 60)
        return obj
