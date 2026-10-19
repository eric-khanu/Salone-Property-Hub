"""Admin configuration for the custom User model."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # ---------------------------------------------------------------- columns
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "phone",
        "company_name",
        "is_active",
        "phone_verified",
        "is_staff",
    )
    list_editable = ("is_active", "phone_verified")
    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "phone_verified",
    )
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
        "company_name",
    )
    ordering = ("-date_joined",)

    # ---------------------------------------------------------------- forms
    # Change form: adds our extra fields to the standard fieldset layout.
    fieldsets = UserAdmin.fieldsets + (
        (
            "Sierra Leone Property Hub",
            {
                "fields": (
                    "role",
                    "phone",
                    "whatsapp_number",
                    "company_name",
                    "phone_verified",
                )
            },
        ),
    )

    # Add form: without this, admins can't set role / company when creating
    # a user directly from /admin/users/user/add/.
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Sierra Leone Property Hub",
            {
                "fields": (
                    "role",
                    "phone",
                    "whatsapp_number",
                    "company_name",
                )
            },
        ),
    )