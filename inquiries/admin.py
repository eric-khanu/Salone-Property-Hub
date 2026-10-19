"""Admin configuration for property inquiries."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Inquiry


@admin.action(description="Mark selected inquiries as read")
def mark_as_read(modeladmin, request, queryset):
    updated = queryset.update(is_read=True)
    modeladmin.message_user(request, f"{updated} inquiry/inquiries marked as read.")


@admin.action(description="Mark selected inquiries as unread")
def mark_as_unread(modeladmin, request, queryset):
    updated = queryset.update(is_read=False)
    modeladmin.message_user(request, f"{updated} inquiry/inquiries marked as unread.")


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    # ---------------------------------------------------------------- columns
    list_display = (
        "created_at",
        "name",
        "property_link",
        "recipient",
        "phone",
        "preview",
        "is_read",
    )
    list_editable = ("is_read",)      # requires is_read in list_display
    list_filter = ("is_read", "created_at")
    search_fields = (
        "name",
        "phone",
        "email",
        "message",
        "property__title",
        "recipient__username",
    )
    date_hierarchy = "created_at"

    # ---------------------------------------------------------------- form
    # property and recipient are set by the request; don't let admins
    # re-route an inquiry after the fact.
    readonly_fields = ("property", "recipient", "created_at")
    raw_id_fields = ("property", "recipient")

    # ---------------------------------------------------------------- actions
    actions = (mark_as_read, mark_as_unread)

    # ---------------------------------------------------------------- helpers
    @admin.display(description="Property", ordering="property__title")
    def property_link(self, obj):
        if not obj.property_id:
            return "—"
        return format_html(
            '<a href="/admin/properties/property/{}/change/">{}</a>',
            obj.property_id,
            obj.property.title,
        )

    @admin.display(description="Message")
    def preview(self, obj):
        text = (obj.message or "").strip()
        if len(text) <= 60:
            return text
        return text[:57] + "…"