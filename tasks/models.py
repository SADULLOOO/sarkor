from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Task(models.Model):
    class Type(models.TextChoices):
        URGENT = "urgent", _("Urgent")
        ONE_OFF = "one_off", _("One-off")
        DELIVERY = "delivery", _("Delivery")

    class Timing(models.TextChoices):
        URGENT = "urgent", _("Urgent")
        TODAY = "today", _("Today")
        SCHEDULED = "scheduled", _("Date and time")

    class Status(models.TextChoices):
        OPEN = "open", _("Looking for executor")
        ASSIGNED = "assigned", _("Executor selected")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")
        CLOSED = "closed", _("Closed")
        CANCELLED = "cancelled", _("Cancelled")

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tasks")
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.ONE_OFF)
    category = models.ForeignKey("catalog.Category", on_delete=models.PROTECT, related_name="tasks")
    description = models.TextField(_("what to do"), max_length=2000)
    voice = models.FileField(upload_to="tasks/voice/", blank=True)

    district = models.ForeignKey("catalog.District", on_delete=models.PROTECT, related_name="tasks")
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    timing = models.CharField(max_length=20, choices=Timing.choices, default=Timing.TODAY)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    # Empty budget means "negotiable".
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "category", "district"])]

    def __str__(self):
        return f"#{self.pk} {self.description[:40]}"

    def is_participant(self, user):
        return user.id in (self.customer_id, self.executor_id)


class TaskPhoto(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="tasks/photos/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Response(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")
        NO_SHOW = "no_show", _("Did not come")

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="responses")
    executor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="responses")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    comment = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["task", "executor"], name="one_response_per_executor"),
        ]

    def __str__(self):
        return f"{self.executor} -> task #{self.task_id}: {self.price}"


class Review(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written"
    )
    target = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received"
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["task", "author"], name="one_review_per_author"),
        ]

    def __str__(self):
        return f"{self.author} -> {self.target}: {self.rating}"
