"""Inquiries sent from a property detail page."""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+?[0-9][0-9\s\-().]{5,25}$",
    message="Enter a valid phone number (digits, spaces, +, -, or parentheses).",
)


class Inquiry(models.Model):
    """A user's message to a property owner.

    ``property`` and ``recipient`` are nullable so an inquiry survives
    deletion of either — the audit trail is kept, only the links break.
    """

    property = models.ForeignKey(
        "properties.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inquiries",
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="received_inquiries",
    )

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, validators=[PHONE_VALIDATOR])
    message = models.TextField(
        max_length=2000,
        help_text="Up to 2000 characters.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["property", "created_at"]),
        ]

    def __str__(self):
        if self.property_id and self.property:
            return f"Inquiry from {self.name} about {self.property.title}"
        return f"Inquiry from {self.name}"