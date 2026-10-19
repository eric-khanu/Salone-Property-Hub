from django.conf import settings
from django.db import models
class Advertisement(models.Model):
    class Placement(models.TextChoices): BANNER='banner','Homepage banner'; SIDEBAR='sidebar','Sidebar'; SPOTLIGHT='spotlight','Company spotlight'
    class Status(models.TextChoices): DRAFT='draft','Draft'; PENDING='pending','Pending approval'; ACTIVE='active','Active'; REJECTED='rejected','Rejected'; EXPIRED='expired','Expired'
    advertiser=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='advertisements'); title=models.CharField(max_length=160); image=models.ImageField(upload_to='advertisements/%Y/%m/'); landing_url=models.URLField(); placement=models.CharField(max_length=12,choices=Placement.choices); plan=models.ForeignKey('subscriptions.Plan',null=True,blank=True,on_delete=models.SET_NULL); status=models.CharField(max_length=12,choices=Status.choices,default=Status.PENDING); starts_at=models.DateTimeField(null=True,blank=True); ends_at=models.DateTimeField(null=True,blank=True); impressions=models.PositiveIntegerField(default=0); clicks=models.PositiveIntegerField(default=0); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']; indexes=[models.Index(fields=['status','placement','starts_at','ends_at'])]
    def __str__(self): return self.title
