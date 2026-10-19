"""Service layer for subscriptions — the only place that activates a payment
or expires entitlements. Views should always go through these helpers."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Payment, Plan, Subscription


# ---------------------------------------------------------------------------
# Activate a verified payment
# ---------------------------------------------------------------------------
@transaction.atomic
def activate_verified_payment(payment, verifier):
    """Turn a verified Payment into a Subscription (idempotent).

    Returns the Subscription, or None if the payment isn't VERIFIED.

    Rules:
      * Activation replaces the user's existing ACTIVE subscription of the
        same kind (LISTING vs AD) — the old one is marked CANCELLED.
      * For LISTING plans, the user's existing non-rejected listings are
        re-slotted into the new quota. Oldest listings win; the rest are
        marked EXPIRED. Every listing's ``subscription_expires_at`` is
        aligned with the new subscription.
      * Safe to call twice: a second call returns the existing subscription.
    """
    # Lock the payment row so two verifiers can't both activate it.
    payment = (
        Payment.objects.select_for_update()
        .select_related("plan", "user")
        .get(pk=payment.pk)
    )

    if payment.status != Payment.Status.VERIFIED:
        return None

    # Already activated? Return the existing subscription (idempotent).
    existing = getattr(payment, "subscription", None)
    if existing:
        return existing

    plan = payment.plan
    start = timezone.now()
    duration_days = max(int(plan.duration_days or 0), 1)  # defensive
    ends_at = start + timedelta(days=duration_days)

    # Cancel any other active subscription of the same kind.
    # NOTE: no select_for_update() — Django ignores it on .update(), and the
    # UPDATE statement is already atomic.
    Subscription.objects.filter(
        user=payment.user,
        status=Subscription.Status.ACTIVE,
        plan__kind=plan.kind,
    ).update(status=Subscription.Status.CANCELLED)

    # Create the new subscription. If two verifiers race past the
    # getattr(payment, 'subscription') check, the unique constraint on
    # payment_id will reject the loser.
    try:
        sub = Subscription.objects.create(
            user=payment.user,
            plan=plan,
            payment=payment,
            starts_at=start,
            ends_at=ends_at,
            listings_allowed=plan.listing_limit if plan.kind == Plan.Kind.LISTING else 0,
        )
    except IntegrityError:
        # Race lost — return the winner's subscription.
        return Subscription.objects.get(payment=payment)

    # ---------------------------------------------------------------- listings
    if plan.kind == Plan.Kind.LISTING:
        # Lazy import to avoid a circular dependency with properties.
        from properties.models import Property

        listings = list(
            Property.objects.filter(owner=payment.user)
            .exclude(status=Property.Status.REJECTED)
            .order_by("created_at", "id")
        )

        to_update = []
        for index, listing in enumerate(listings):
            if index < sub.listings_allowed:
                listing.status = Property.Status.PUBLISHED
            else:
                listing.status = Property.Status.EXPIRED
            # Always align the expiry with the new subscription, so that
            # upgrades don't leave stale dates behind.
            listing.subscription_expires_at = sub.ends_at
            to_update.append(listing)

        if to_update:
            Property.objects.bulk_update(
                to_update,
                fields=["status", "subscription_expires_at", "updated_at"],
            )

        # listings_used = how many slots are consumed by existing listings.
        sub.listings_used = min(len(listings), sub.listings_allowed)
        sub.save(update_fields=["listings_used"])

    # `verifier` is intentionally not stored on the Subscription — the audit
    # trail lives on Payment.verified_by / verified_at. Kept in the signature
    # so callers can be updated independently if we add the column later.
    return sub


# ---------------------------------------------------------------------------
# Current subscription lookup
# ---------------------------------------------------------------------------
def current_subscription(user, kind=Plan.Kind.LISTING):
    """Return the user's current active subscription of the given kind, or None."""
    now = timezone.now()
    return (
        Subscription.objects.filter(
            user=user,
            plan__kind=kind,
            status=Subscription.Status.ACTIVE,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .order_by("-ends_at")
        .first()
    )


# ---------------------------------------------------------------------------
# Expiry sweep (call from a cron / management command)
# ---------------------------------------------------------------------------
def expire_subscriptions():
    """Mark expired subscriptions, listings, and ads as EXPIRED.

    Safe to run repeatedly. Returns a dict of counts for logging.
    """
    now = timezone.now()

    subs_count = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE, ends_at__lte=now
    ).update(status=Subscription.Status.EXPIRED)

    # Lazy import — properties depends on subscriptions in the other direction.
    from properties.models import Property

    listings_count = Property.objects.filter(
        status=Property.Status.PUBLISHED,
        subscription_expires_at__lte=now,
    ).update(status=Property.Status.EXPIRED)

    from advertisements.models import Advertisement

    ads_count = Advertisement.objects.filter(
        status=Advertisement.Status.ACTIVE, ends_at__lte=now
    ).update(status=Advertisement.Status.EXPIRED)

    return {
        "subscriptions_expired": subs_count,
        "listings_expired": listings_count,
        "ads_expired": ads_count,
    }