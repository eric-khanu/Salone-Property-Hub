"""Property listings and their images."""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


# Accepts: +232 76 123 456, 076 123456, (076) 123456, etc.
PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+?[0-9][0-9\s\-().]{5,25}$",
    message="Enter a valid phone number (digits, spaces, +, -, or parentheses).",
)


class Property(models.Model):
    """A property listing. Owner-scoped; visible to the public only when published."""

    # ---------------------------------------------------------------- choices
    class ListingType(models.TextChoices):
        RENT = "rent", "For rent"
        SALE = "sale", "For sale"

    class PropertyType(models.TextChoices):
        HOUSE = "house", "House"
        APARTMENT = "apartment", "Apartment"
        LAND = "land", "Land"
        COMMERCIAL = "commercial", "Commercial"
        ROOM = "room", "Room"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending approval"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    class Currency(models.TextChoices):
        SLE = "nLE", "NLE"
        USD = "$", "$"

    # ---------------------------------------------------------------- identity
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        editable=False,
        db_index=True,
        help_text="Generated automatically from the title.",
    )

    # ---------------------------------------------------------------- description
    description = models.TextField()
    listing_type = models.CharField(max_length=10, choices=ListingType.choices)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)

    # ---------------------------------------------------------------- pricing
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.SLE
    )

    # ---------------------------------------------------------------- location
    region = models.CharField(max_length=80, default="Western Area")
    district_or_city = models.CharField(max_length=100, default="Freetown")
    neighborhood = models.CharField(max_length=120, blank=True)

    # ---------------------------------------------------------------- features
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=0)
    area_sqft = models.PositiveIntegerField(null=True, blank=True)
    amenities = models.JSONField(
        default=list,
        blank=True,
        help_text='List of strings, e.g. ["Wifi", "Parking", "Generator"].',
    )

    # ---------------------------------------------------------------- contact
    contact_phone = models.CharField(max_length=30, validators=[PHONE_VALIDATOR])
    whatsapp_number = models.CharField(max_length=30, blank=True)

    # ---------------------------------------------------------------- state
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    featured = models.BooleanField(default=False)
    subscription_expires_at = models.DateTimeField(
        null=True, blank=True, help_text="When the listing's paid window ends."
    )

    # ---------------------------------------------------------------- counters
    # Maintained by the view / inquiry logic — not by save().
    views = models.PositiveIntegerField(default=0)
    inquiry_count = models.PositiveIntegerField(default=0)

    # ---------------------------------------------------------------- timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-featured", "-created_at"]
        indexes = [
            models.Index(fields=["status", "listing_type", "property_type"]),
            models.Index(fields=["region", "district_or_city", "neighborhood"]),
            models.Index(fields=["price"]),
            models.Index(fields=["created_at"]),
        ]

    # ---------------------------------------------------------------- methods
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("properties:detail", kwargs={"slug": self.slug})

    # ---------------------------------------------------------------- slug logic
    def _wants_slug_regen(self, update_fields):
        """Return True if the slug should be (re)computed for this save."""
        # First save — always generate.
        if self._state.adding:
            return True
        # If the caller restricted update_fields, only touch the slug
        # when 'title' is included (or explicitly when 'slug' is).
        if update_fields is not None:
            update_fields = set(update_fields)
            return "title" in update_fields or "slug" in update_fields
        # Full save — regenerate only if the title actually changed.
        if not self.pk:
            return True
        old_title = (
            type(self).objects.filter(pk=self.pk)
            .values_list("title", flat=True)
            .first()
        )
        return old_title != self.title

    def _unique_slug(self, base):
        """Turn ``base`` into a slug that no other Property row uses."""
        base = base[:200].strip("-") or "property"
        candidate = base
        suffix = 2
        qs = type(self).objects.exclude(pk=self.pk)
        while qs.filter(slug=candidate).exists():
            candidate = f"{base[:196]}-{suffix}"[:200]
            suffix += 1
        return candidate

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if self._wants_slug_regen(update_fields):
            self.slug = self._unique_slug(slugify(self.title or ""))
            # If the caller restricted update_fields, make sure slug is included.
            if update_fields is not None:
                update_fields = set(update_fields) | {"slug"}
                kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

    # ---------------------------------------------------------------- amenities
    def clean_amenities(self):
        """Return amenities as a list of non-empty strings, whatever shape it's in."""
        raw = self.amenities
        if isinstance(raw, str):
            raw = [s.strip() for s in raw.split(",")]
        if not isinstance(raw, list):
            return []
        return [str(a).strip() for a in raw if str(a).strip()]


class PropertyImage(models.Model):
    """One image belonging to a property. Ordered by sort_order then id."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    # upload_to uses %Y/%m — same filename in the same month gets a random suffix
    image = models.ImageField(upload_to="properties/%Y/%m/")
    alt_text = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.alt_text or f"Image for {self.property.title} ({self.pk})"