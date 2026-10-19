"""Admin configuration for property listings."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Property, PropertyImage


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------
class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0
    fields = ("image", "thumbnail", "alt_text", "sort_order")
    readonly_fields = ("thumbnail",)

    @admin.display(description="Preview")
    def thumbnail(self, obj):
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" style="height:60px;border-radius:4px;" />',
            obj.image.url,
        )


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "listing_type",
        "property_type",
        "price",
        "currency",
        "region",
        "district_or_city",
        "status",
        "featured",
        "views",
        "created_at",
    )
    list_editable = ("status", "featured")   # requires both to be in list_display
    list_filter = (
        "status",
        "featured",
        "listing_type",
        "property_type",
        "region",
        "currency",
    )
    search_fields = (
        "title",
        "slug",
        "description",
        "neighborhood",
        "district_or_city",
        "owner__username",
        "owner__email",
    )
    date_hierarchy = "created_at"
    inlines = [PropertyImageInline]

    # slug is auto-generated in Property.save(); show it, don't let admins edit it.
    readonly_fields = (
        "slug",
        "views",
        "inquiry_count",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Listing", {
            "fields": (
                "title",
                "slug",
                "owner",
                "description",
                "listing_type",
                "property_type",
            ),
        }),
        ("Pricing", {
            "fields": ("price", "currency"),
        }),
        ("Location", {
            "fields": ("region", "district_or_city", "neighborhood"),
        }),
        ("Features", {
            "fields": ("bedrooms", "bathrooms", "area_sqft", "amenities"),
        }),
        ("Contact", {
            "fields": ("contact_phone", "whatsapp_number"),
        }),
        ("Visibility & moderation", {
            "fields": ("status", "featured", "subscription_expires_at"),
        }),
        ("Metrics", {
            "fields": ("views", "inquiry_count"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------------
# PropertyImage (direct access via /admin/properties/propertyimage/)
# ---------------------------------------------------------------------------
@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("property", "thumbnail", "alt_text", "sort_order")
    list_filter = ("property__status", "property__region")
    search_fields = ("property__title", "alt_text")
    readonly_fields = ("thumbnail",)

    @admin.display(description="Preview")
    def thumbnail(self, obj):
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" style="height:60px;border-radius:4px;" />',
            obj.image.url,
        )