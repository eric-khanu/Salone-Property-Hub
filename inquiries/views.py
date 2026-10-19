"""Views for submitting inquiries from a property detail page."""

import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect

from properties.models import Property

from .forms import InquiryForm

logger = logging.getLogger(__name__)


def send_property_inquiry(request, slug):
    """Create an Inquiry for a published property and notify the owner.

    Returns a redirect on success, or ``None`` if the request wasn't a valid
    POST — the caller is expected to fall back to rendering the detail page.

    NOTE: ``properties.views.detail`` currently duplicates this logic inline;
    if you route to this view, consider having ``detail`` delegate here so
    there's only one implementation.
    """
    prop = get_object_or_404(
        Property.objects.select_related("owner"),
        slug=slug,
        status=Property.Status.PUBLISHED,
    )

    # Don't let owners submit inquiries to their own listings.
    if request.user.is_authenticated and request.user.pk == prop.owner_id:
        return None

    form = InquiryForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.property = prop
        inquiry.recipient = prop.owner
        inquiry.save()

        # Atomic increment — avoids lost updates under concurrency.
        Property.objects.filter(pk=prop.pk).update(
            inquiry_count=F("inquiry_count") + 1
        )

        # Notify the owner, but never let a mail failure roll back the
        # inquiry. ``fail_silently=True`` covers SMTP errors; the try/except
        # covers backend misconfigurations (e.g. missing EMAIL_HOST).
        if prop.owner and prop.owner.email:
            try:
                send_mail(
                    subject=f"New inquiry: {prop.title}",
                    message=(
                        f"{inquiry.name} ({inquiry.phone}) wrote:\n\n"
                        f"{inquiry.message}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[prop.owner.email],
                    fail_silently=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to email inquiry notification for property %s: %s",
                    prop.pk,
                    exc,
                )

        messages.success(
            request, "Your inquiry has been sent to the property contact."
        )
        return redirect(prop.get_absolute_url())

    return None