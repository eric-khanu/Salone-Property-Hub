"""Custom user model: role, contact details, optional company info."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


# Matches the pattern used on Property.contact_phone — kept here to avoid a
# circular import (properties.models imports the user model indirectly).
PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+?[0-9][0-9\s\-().]{5,25}$",
    message="Enter a valid phone number (digits, spaces, +, -, or parentheses).",
)


class User(AbstractUser):
    """Application user. `role` determines which plans and actions are allowed."""

    class Role(models.TextChoices):
        OWNER = "owner", "Property owner"
        AGENT = "agent", "Property agent"
        ADVERTISER = "advertiser", "Company advertiser"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True,
        default="",
        help_text="Required to create listings or purchase a plan.",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        validators=[PHONE_VALIDATOR],
        help_text="Include country code, e.g. +232...",
    )
    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
        validators=[PHONE_VALIDATOR],
    )
    company_name = models.CharField(max_length=180, blank=True)
    phone_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return (self.get_full_name() or self.username or self.email).strip()

    # ---- Convenience helpers (used in templates / views / admin) ----
    @property
    def is_advertiser(self):
        return self.role == self.Role.ADVERTISER

    @property
    def is_lister(self):
        return self.role in (self.Role.OWNER, self.Role.AGENT)