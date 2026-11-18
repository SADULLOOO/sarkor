from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

MAX_IMAGE_SIZE_MB = 5


def validate_image_size(image):
    if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(_("Image is too large, max %(size)s MB.") % {"size": MAX_IMAGE_SIZE_MB})
