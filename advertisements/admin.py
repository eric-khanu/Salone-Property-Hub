from django.contrib import admin
from .models import Advertisement
@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display=('title','advertiser','placement','status','starts_at','ends_at','impressions','clicks')
    list_filter=('status','placement'); search_fields=('title','advertiser__username'); readonly_fields=('impressions','clicks','created_at')
