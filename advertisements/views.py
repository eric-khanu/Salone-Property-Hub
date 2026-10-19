from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from subscriptions.services import current_subscription
from subscriptions.models import Plan
from .models import Advertisement
from .forms import AdvertisementForm
@login_required
def create(request):
    if request.user.role!='advertiser' and not request.user.is_staff:
        messages.error(request,'Company advertiser accounts are required to manage advertisements.'); return redirect('dashboard:home')
    sub=current_subscription(request.user,Plan.Kind.AD)
    if not sub:
        messages.error(request,'An active advertising subscription is required before you can submit an ad.'); return redirect('subscriptions:plans')
    form=AdvertisementForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        ad=form.save(commit=False); ad.advertiser=request.user; ad.plan=sub.plan; ad.status=Advertisement.Status.ACTIVE; ad.starts_at=timezone.now(); ad.ends_at=sub.ends_at; ad.save()
        messages.success(request,'Your advertisement is now active.'); return redirect('dashboard:home')
    return render(request,'advertisements/form.html',{'form':form})
def click(request,pk):
    ad=get_object_or_404(Advertisement,pk=pk,status=Advertisement.Status.ACTIVE,ends_at__gt=timezone.now()); Advertisement.objects.filter(pk=ad.pk).update(clicks=F('clicks')+1); return redirect(ad.landing_url)
