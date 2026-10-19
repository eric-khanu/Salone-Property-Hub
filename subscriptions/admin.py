"""Admin for plans, payments, and subscriptions."""

from django.contrib import admin, messages
from django.db import IntegrityError
from django.utils import timezone

from .models import Payment, Plan, Subscription
from .services import activate_verified_payment


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "price_sle",
        "listing_limit",
        "duration_days",
        "is_trial",
        "active",
    )
    list_editable = ("active",)
    list_filter = ("kind", "active", "is_trial")
    search_fields = ("name",)
    fieldsets = (
        (None, {
            "fields": ("name", "kind", "description", "active"),
        }),
        ("Pricing and limits", {
            "fields": ("price_sle", "duration_days", "listing_limit", "is_trial"),
        }),
    )


# ---------------------------------------------------------------------------
# Verify payments (admin action)
# ---------------------------------------------------------------------------
@admin.action(description="Verify selected offline payments and activate plans")
def verify_payments(modeladmin, request, queryset):
    """Verify each PENDING payment and activate its subscription.

    Per-payment errors are collected so one bad row doesn't block the rest.
    """
    verified_count = 0
    errors = []

    for payment in queryset.select_related("plan", "user"):
        if payment.status != Payment.Status.PENDING:
            continue

        # Flip the payment to VERIFIED first (this is what activate expects).
        payment.status = Payment.Status.VERIFIED
        payment.verified_at = timezone.now()
        payment.verified_by = request.user
        payment.save(update_fields=["status", "verified_at", "verified_by"])

        try:
            activate_verified_payment(payment, request.user)
            verified_count += 1
        except Exception as exc:  # noqa: BLE001 — report and continue
            errors.append(f"{payment.reference}: {exc}")

    if verified_count:
        modeladmin.message_user(
            request,
            f"{verified_count} payment(s) verified and activated.",
            messages.SUCCESS,
        )
    for err in errors:
        modeladmin.message_user(request, err, messages.ERROR)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "user",
        "plan",
        "amount_sle",
        "provider",
        "status",
        "created_at",
        "verified_by",
        "proof_link",
    )
    list_filter = ("status", "provider", "plan__kind")
    search_fields = ("reference", "user__username", "notes", "payer_name")
    readonly_fields = (
        "reference",
        "created_at",
        "verified_at",
        "verified_by",
        "proof",
    )
    actions = [verify_payments]

    @admin.display(description="Proof")
    def proof_link(self, obj):
        if not obj.proof:
            return "—"
        from django.utils.html import format_html
        return format_html('<a href="{}" target="_blank" rel="noopener">View</a>', obj.proof.url)

    def save_model(self, request, obj, form, change):
        """Auto-stamp verification fields and (only on transition) activate.

        Activation is triggered *only* when status changes from something else
        to VERIFIED — not on every edit of an already-verified payment.
        """
        was_verified = False
        if change and obj.pk:
            was_verified = Payment.objects.filter(
                pk=obj.pk, status=Payment.Status.VERIFIED
            ).exists()

        if obj.status == Payment.Status.VERIFIED and not was_verified:
            obj.verified_at = obj.verified_at or timezone.now()
            obj.verified_by = obj.verified_by or request.user

        super().save_model(request, obj, form, change)

        if obj.status == Payment.Status.VERIFIED and not was_verified:
            try:
                activate_verified_payment(obj, request.user)
            except Exception as exc:  # noqa: BLE001
                self.message_user(
                    request,
                    f"Payment verified but activation failed: {exc}",
                    messages.ERROR,
                )


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan",
        "payment",
        "status",
        "starts_at",
        "ends_at",
        "listings_allowed",
        "listings_used",
    )
    list_filter = ("status", "plan__kind")
    search_fields = ("user__username", "plan__name", "payment__reference")
    readonly_fields = ("starts_at", "created_at")
    date_hierarchy = "created_at"
    raw_id_fields = ("payment",)