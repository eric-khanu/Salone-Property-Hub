"""Subscription plans list and offline payment submission."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import PaymentSubmissionForm
from .models import Payment, Plan
from .services import current_subscription

logger = logging.getLogger(__name__)


# Roles allowed to purchase each kind of plan.
# Keys are Plan.Kind values (strings) — if you rename a Kind value,
# update these keys too or every user will be blocked from buying.
ALLOWED_ROLES = {
    Plan.Kind.LISTING.value: {"owner", "agent"},
    Plan.Kind.AD.value: {"advertiser"},
}


def _plans_url(kind):
    """Build the plans list URL with the ?kind= query string."""
    return f"{reverse('subscriptions:plans')}?kind={kind}"


def plans(request):
    """List active non-trial plans, with the user's current plan and payments."""
    kind = request.GET.get("kind", Plan.Kind.LISTING.value)
    if kind not in Plan.Kind.values:
        kind = Plan.Kind.LISTING.value

    plan_qs = Plan.objects.filter(active=True, kind=kind, is_trial=False)

    active = None
    payments = Payment.objects.none()
    if request.user.is_authenticated:
        # current_subscription accepts either a string or the enum; the string
        # form is what the rest of this view uses.
        active = current_subscription(request.user, kind)
        payments = (
            Payment.objects.filter(user=request.user)
            .select_related("plan")
            .order_by("-created_at")[:10]
        )

    return render(
        request,
        "subscriptions/plans.html",
        {
            "plans": plan_qs,
            "payments": payments,
            "active_subscription": active,
            "kind": kind,
        },
    )


@login_required
def submit_payment(request, plan_id):
    """Submit an offline payment for a specific plan."""
    plan = get_object_or_404(Plan, pk=plan_id, active=True, is_trial=False)

    # -- Role guard -------------------------------------------------------
    allowed_roles = ALLOWED_ROLES.get(plan.kind, set())
    if not allowed_roles:
        # A new Plan.Kind exists but nobody was added to ALLOWED_ROLES.
        # Fail safely *and* loud so it shows up in logs.
        logger.warning(
            "No ALLOWED_ROLES configured for plan kind %r (plan %s).",
            plan.kind,
            plan.pk,
        )

    if request.user.role not in allowed_roles and not request.user.is_staff:
        messages.error(
            request, "This plan is not available for your account type."
        )
        return redirect(_plans_url(plan.kind))

    # -- Form -------------------------------------------------------------
    form = PaymentSubmissionForm(
        request.POST or None,
        request.FILES or None,
        plan=plan,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        try:
            payment = form.save()
        except IntegrityError as exc:
            # The expected case is a reference collision (UUID or duplicate
            # user submission). Anything else — FK violation, check constraint —
            # should bubble up so it isn't silently disguised as "try again".
            error_str = str(exc).lower()
            if "reference" in error_str or "unique" in error_str:
                form.add_error(
                    None, "Could not save this payment. Please try again."
                )
            else:
                raise
        else:
            messages.success(
                request,
                f"Payment reference {payment.reference} submitted. "
                "Your access will be activated after the administrator "
                "verifies the offline payment.",
            )
            return redirect("subscriptions:plans")

    return render(
        request,
        "subscriptions/payment_form.html",
        {"form": form, "plan": plan},
    )