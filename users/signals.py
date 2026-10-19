"""Signal handlers for the users app."""

import logging
from datetime import timedelta

from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User

logger = logging.getLogger(__name__)


# Trial plan defaults (used only if the trial plan doesn't already exist).
TRIAL_PLAN_DEFAULTS = {
    "name": "Free Trial — 10 Listings",
    "duration_days": 14,
    "price_sle": 0,
    "listing_limit": 10,
    "active": True,
    "description": "14-day test plan with up to 10 property listings.",
}


@receiver(
    post_save,
    sender=User,
    dispatch_uid="users.assign_trial",
)
def assign_trial(sender, instance, created, **kwargs):
    """Grant a free listing trial the first time a lister account is created."""
    if not created:
        return
    if instance.role not in (User.Role.OWNER, User.Role.AGENT):
        return

    # Import here to avoid a circular dependency
    # (subscriptions imports users via AUTH_USER_MODEL).
    from subscriptions.models import Plan, Subscription

    try:
        plan, _ = Plan.objects.get_or_create(
            kind=Plan.Kind.LISTING,
            is_trial=True,
            defaults=TRIAL_PLAN_DEFAULTS,
        )
    except Plan.MultipleObjectsReturned:
        # More than one trial plan exists — pick the cheapest active one.
        logger.warning(
            "Multiple trial plans exist; picking the most recent one for user %s",
            instance.pk,
        )
        plan = (
            Plan.objects.filter(kind=Plan.Kind.LISTING, is_trial=True, active=True)
            .order_by("-created_at")
            .first()
        )
        if plan is None:
            logger.error("No usable trial plan found; skipping trial for %s", instance.pk)
            return

    # Idempotent: get_or_create on (user, plan) so a double-fire can't create two.
    start = timezone.now()
    duration_days = max(int(plan.duration_days or 0), 1)
    try:
        Subscription.objects.get_or_create(
            user=instance,
            plan=plan,
            defaults={
                "starts_at": start,
                "ends_at": start + timedelta(days=duration_days),
                "listings_allowed": plan.listing_limit,
                "status": Subscription.Status.ACTIVE,
            },
        )
    except IntegrityError:
        # Extremely rare — another signal handler created the same row.
        logger.warning("Trial subscription already exists for user %s", instance.pk)