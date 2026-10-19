"""Public property views: homepage listing, detail, create, edit, image delete."""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from PIL import Image, UnidentifiedImageError

from advertisements.models import Advertisement
from inquiries.forms import InquiryForm
from subscriptions.models import Plan
from subscriptions.services import current_subscription

from .forms import MultipleImageField, PropertyForm
from .models import Property, PropertyImage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_decimal(value):
    """Return a Decimal or None if the string isn't a valid number."""
    if value in (None, ""):
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _unique_slug(title, exclude_pk=None):
    base = slugify(title or "")[:180] or "property"
    candidate = base
    suffix = 2
    qs = Property.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _validate_image(f):
    """Raise ValidationError if the file isn't a JPG/PNG/WebP under 8 MB."""
    if f.size > 8 * 1024 * 1024:
        raise ValidationError("Each photo must be 8 MB or smaller.")
    try:
        f.seek(0)
        with Image.open(f) as img:
            img.load()  # forces decode; raises for truncated files
            fmt = img.format
        f.seek(0)
    except (UnidentifiedImageError, OSError):
        raise ValidationError("One of the uploaded files is not a valid image.")
    if fmt not in ("JPEG", "PNG", "WEBP"):
        raise ValidationError("Photos must be JPG, PNG or WebP images.")


def _save_images(request, obj):
    """Validate all files first, then create PropertyImage rows."""
    files = request.FILES.getlist("images")
    if not files:
        return
    if len(files) > 12:
        raise ValidationError("Upload a maximum of 12 photos per save.")

    # Validate *everything* before creating any rows, so a bad file can't
    # leave half-created images / orphaned files on disk.
    for f in files:
        _validate_image(f)

    for f in files:
        PropertyImage.objects.create(property=obj, image=f, alt_text=obj.title)


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------
def home(request):
    now = timezone.now()

    qs = (
        Property.objects.filter(status=Property.Status.PUBLISHED)
        .filter(
            Q(subscription_expires_at__isnull=True)
            | Q(subscription_expires_at__gt=now)
        )
        .prefetch_related("images")
    )

    q = request.GET.get("q", "").strip()
    listing = request.GET.get("listing", "")
    ptype = request.GET.get("type", "")
    region = request.GET.get("region", "")
    currency = request.GET.get("currency", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(neighborhood__icontains=q)
            | Q(district_or_city__icontains=q)
            | Q(region__icontains=q)
        )
    if listing in ("rent", "sale"):
        qs = qs.filter(listing_type=listing)
    if ptype in dict(Property.PropertyType.choices):
        qs = qs.filter(property_type=ptype)
    if region:
        qs = qs.filter(region__icontains=region)
    if currency in ("SLE", "USD"):
        qs = qs.filter(currency=currency)

    min_dec = _parse_decimal(min_price)
    max_dec = _parse_decimal(max_price)
    if min_dec is not None:
        qs = qs.filter(price__gte=min_dec)
    if max_dec is not None:
        qs = qs.filter(price__lte=max_dec)

    # ---- Ads: fetch, then bump impressions in one query per placement ----
    ads = list(
        Advertisement.objects.filter(
            status=Advertisement.Status.ACTIVE,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .select_related("advertiser")
        .order_by("-created_at")[:12]
    )
    if ads:
        Advertisement.objects.filter(pk__in=[a.pk for a in ads]).update(
            impressions=F("impressions") + 1
        )

    banner_ads = [a for a in ads if a.placement == "banner"]
    sidebar_ads = [a for a in ads if a.placement == "sidebar"]
    spotlight_ads = [a for a in ads if a.placement == "spotlight"]

    return render(
        request,
        "properties/home.html",
        {
            "properties": qs[:60],
            "q": q,
            "listing": listing,
            "ptype": ptype,
            "region": region,
            "currency": currency,
            "min_price": min_price,
            "max_price": max_price,
            "banner_ads": banner_ads,
            "sidebar_ads": sidebar_ads,
            "spotlight_ads": spotlight_ads,
        },
    )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
def detail(request, slug):
    prop = get_object_or_404(
        Property.objects.select_related("owner").prefetch_related("images"),
        slug=slug,
        status=Property.Status.PUBLISHED,
    )

    if request.method == "POST":
        form = InquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.property = prop
            inquiry.recipient = prop.owner
            inquiry.save()
            Property.objects.filter(pk=prop.pk).update(
                inquiry_count=F("inquiry_count") + 1
            )
            if prop.owner.email:
                send_mail(
                    f"New inquiry: {prop.title}",
                    f"{inquiry.name} ({inquiry.phone}) wrote:\n{inquiry.message}",
                    settings.DEFAULT_FROM_EMAIL,
                    [prop.owner.email],
                    fail_silently=True,
                )
            messages.success(
                request, "Your inquiry has been sent to the property contact."
            )
            return redirect(prop.get_absolute_url())
    else:
        form = InquiryForm()

    # Count a view only when the viewer isn't the owner.
    if not request.user.is_authenticated or request.user.pk != prop.owner_id:
        Property.objects.filter(pk=prop.pk).update(views=F("views") + 1)

    return render(
        request,
        "properties/detail.html",
        {"property": prop, "form": form},
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@login_required
def create(request):
    if request.user.role not in ("owner", "agent") and not request.user.is_staff:
        messages.error(
            request, "Only property owners and agents can add listings."
        )
        return redirect("dashboard:home")

    sub = current_subscription(request.user, Plan.Kind.LISTING)
    if not sub or sub.listings_remaining <= 0:
        messages.error(
            request,
            "Your listing plan is expired or its listing allowance is used. "
            "Choose a plan and submit offline payment for verification.",
        )
        return redirect("subscriptions:plans")

    form = PropertyForm(request.POST or None)
    image_field = MultipleImageField(required=False)

    if request.method == "POST" and form.is_valid():
        try:
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.status = Property.Status.PUBLISHED
            obj.subscription_expires_at = sub.ends_at
            obj.slug = _unique_slug(obj.title)
            obj.save()

            _save_images(request, obj)  # validates all files before creating any

            sub.listings_used = F("listings_used") + 1
            sub.save(update_fields=["listings_used"])

            messages.success(
                request,
                "Your property is now published. You can edit it or add "
                "more photos from your dashboard.",
            )
            return redirect("dashboard:home")
        except ValidationError as exc:
            # If the object was created but images failed validation,
            # remove it so no half-saved listing remains.
            if "obj" in locals() and obj.pk:
                obj.delete()
            form.add_error(None, exc)

    return render(
        request,
        "properties/form.html",
        {"form": form, "heading": "Add a property", "image_field": image_field},
    )


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------
@login_required
def edit(request, pk):
    obj = get_object_or_404(Property, pk=pk, owner=request.user)
    form = PropertyForm(request.POST or None, instance=obj)
    image_field = MultipleImageField(required=False)

    if request.method == "POST" and form.is_valid():
        try:
            item = form.save(commit=False)
            # Regenerate slug if the title changed (matches Property.save()
            # behaviour, but we call it here so the form's save doesn't fight
            # the model logic).
            if item.pk and item.title != obj.title:
                item.slug = _unique_slug(item.title, exclude_pk=item.pk)
            item.save()
            _save_images(request, item)
            messages.success(
                request,
                "Property details saved. Your published listing remains live.",
            )
            return redirect("dashboard:home")
        except ValidationError as exc:
            form.add_error(None, exc)

    return render(
        request,
        "properties/form.html",
        {
            "form": form,
            "heading": "Edit property",
            "property": obj,
            "image_field": image_field,
        },
    )


# ---------------------------------------------------------------------------
# Delete image
# ---------------------------------------------------------------------------
@login_required
@require_POST
def delete_image(request, pk):
    image = get_object_or_404(PropertyImage, pk=pk, property__owner=request.user)
    prop = image.property
    image.image.delete(save=False)
    image.delete()
    messages.success(request, "Photo deleted.")
    return redirect("properties:edit", pk=prop.pk)