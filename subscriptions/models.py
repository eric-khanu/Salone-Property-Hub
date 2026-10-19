"""Plans, subscriptions, and offline payments for SL Property Hub."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

def generate_reference():
    """Return a unique string reference for a Payment."""
    return str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
class Plan(models.Model):
    """A purchasable plan (either a listing allowance or an ad campaign slot)."""

    class Kind(models.TextChoices):
        LISTING = "listing", "Property and land listings"
        AD = "ad", "Company advertising"

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=Kind.choices)

    duration_days = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text=(
            "Access duration in days; the subscription expires even if the "
            "listing quota remains unused."
        ),
    )
    price_sle = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    listing_limit = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Number of listings included for listing plans. "
            "For AD plans this value is ignored — set it to 0. "
            "For LISTING plans, 0 means no listings can be created."
        ),
    )

    is_trial = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    description = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "price_sle", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"

    def clean(self):
        # Ad plans shouldn't carry a listing quota.
        if self.kind == self.Kind.AD and self.listing_limit:
            raise ValidationError(
                {"listing_limit": "Ad plans must set listing_limit to 0."}
            )


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------
class Subscription(models.Model):
    """A user's active/past entitlement. Created after a Payment is verified."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    payment = models.OneToOneField(
        "subscriptions.Payment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subscription",
        help_text="The verified payment that granted this subscription, if any.",
    )

    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()

    listings_allowed = models.PositiveIntegerField(default=0)
    listings_used = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status", "ends_at"])]

    def __str__(self):
        return f"{self.user} — {self.plan} ({self.status})"

    # ---- Convenience helpers ----
    @property
    def is_current(self):
        return self.status == self.Status.ACTIVE and self.ends_at > timezone.now()

    @property
    def listings_remaining(self):
        return max(0, self.listings_allowed - self.listings_used)

    def clean(self):
        # Business invariant: a subscription attached to a Payment should
        # only be created for VERIFIED payments (enforced by the service layer,
        # but validated here so admin saves don't skip it).
        if self.payment_id and self.payment.status != Payment.Status.VERIFIED:
            raise ValidationError(
                {"payment": "A subscription can only link to a verified payment."}
            )


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
class Payment(models.Model):
    """An offline payment submitted by a user and verified by an admin."""

    class Provider(models.TextChoices):
        ORANGE = "orange_money", "Orange Money"
        AFRI = "afrimoney", "AfriMoney"
        BANK = "bank", "Bank transfer"
        MANUAL = "manual", "Other offline payment"

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting verification"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="payments"
    )

    provider = models.CharField(max_length=20, choices=Provider.choices)
    amount_sle = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    # Stored as str() so unsaved and loaded instances always return a string.
    reference = models.CharField(
        max_length=120,
        unique=True,
        default=generate_reference,   # ← was: default=lambda: str(uuid.uuid4())
        editable=False,
    )

    payer_name = models.CharField(max_length=160, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(
        blank=True,
        help_text="Transaction ID or details for the administrator to verify.",
    )
    # Accepts a photo or a PDF — content-type validation is done in the form.
    proof = models.FileField(
        upload_to="payment_proofs/%Y/%m/",
        blank=True,
    )

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.reference} — {self.get_status_display()}"

    def clean(self):
        # verified_at and verified_by must be consistent with status.
        if self.status == self.Status.VERIFIED and not self.verified_at:
            raise ValidationError(
                {"verified_at": "Set the verification timestamp."}
            )
        if self.status != self.Status.VERIFIED and self.verified_at:
            raise ValidationError(
                {"verified_at": "Only verified payments can have a timestamp."}
            )

    def save(self, *args, **kwargs):
        # Auto-stamp verified_at when the status flips to VERIFIED, so callers
        # can't forget (and rejections never carry a timestamp).
        if self.status == self.Status.VERIFIED and not self.verified_at:
            self.verified_at = timezone.now()
        elif self.status != self.Status.VERIFIED:
            self.verified_at = None
        super().save(*args, **kwargs)