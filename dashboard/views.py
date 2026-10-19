"""Dashboard views — the user's workspace page."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone  # kept: used by future date filters

from advertisements.models import Advertisement
from inquiries.models import Inquiry
from properties.models import Property
from subscriptions.models import Payment, Plan
from subscriptions.services import current_subscription


@login_required
def home(request):
    user = request.user
    is_advertiser = user.role == "advertiser"

    # ------------------------------------------------------------------
    # Querysets
    # ------------------------------------------------------------------
    properties = (
        Property.objects.filter(owner=user)
        .order_by("-created_at")  # drop if Property.Meta.ordering is set
    )
    ads = (
        Advertisement.objects.filter(advertiser=user)
        .order_by("-created_at")  # drop if Advertisement.Meta.ordering is set
    )
    inquiries = (
        Inquiry.objects.filter(recipient=user)
        .select_related("property")
        .order_by("-created_at")  # drop if Inquiry.Meta.ordering is set
    )

    # ------------------------------------------------------------------
    # Aggregates — single query instead of three separate .count() calls
    # ------------------------------------------------------------------
    stats = properties.aggregate(
        property_count=Count("id"),
        published_count=Count("id", filter=__import__("django.db.models", fromlist=["Q"]).Q(status="published")),
        views_total=Coalesce(Sum("views"), 0),
    )

    # ------------------------------------------------------------------
    # Subscription / payments
    # ------------------------------------------------------------------
    kind = Plan.Kind.AD if is_advertiser else Plan.Kind.LISTING
    subscription = current_subscription(user, kind)

    payments = (
        Payment.objects.filter(user=user)
        .select_related("plan")
        .order_by("-created_at")[:5]  # drop order_by if Payment.Meta.ordering is set
    )

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    return render(
        request,
        "dashboard/home.html",
        {
            "properties": properties,
            "ads": ads,
            "inquiries": inquiries[:8],
            "property_count": stats["property_count"],
            "published_count": stats["published_count"],
            "views_total": stats["views_total"],
            "inquiry_count": inquiries.count(),
            "ads_count": ads.count(),
            "subscription": subscription,
            "payments": payments,
            "is_advertiser": is_advertiser,
        },
    )