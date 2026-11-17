from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _


class TranslatedNameMixin(models.Model):
    name_tg = models.CharField(_("name (tg)"), max_length=100)
    name_ru = models.CharField(_("name (ru)"), max_length=100)

    class Meta:
        abstract = True

    @property
    def name(self):
        if translation.get_language() == "tg":
            return self.name_tg
        return self.name_ru

    def __str__(self):
        return self.name_ru


class Category(TranslatedNameMixin):
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text=_("Icon name used by the frontend"))
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "name_ru"]
        verbose_name = _("category")
        verbose_name_plural = _("categories")


class District(TranslatedNameMixin):
    slug = models.SlugField(unique=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name_ru"]
        verbose_name = _("district")
        verbose_name_plural = _("districts")
