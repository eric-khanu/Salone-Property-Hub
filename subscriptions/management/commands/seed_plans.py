from django.core.management.base import BaseCommand
from subscriptions.models import Plan
class Command(BaseCommand):
    help='Create the default 14-day, 10-listing trial plan if missing.'
    def handle(self,*args,**options):
        plan,created=Plan.objects.get_or_create(kind=Plan.Kind.LISTING,is_trial=True,defaults={'name':'Free Trial — 10 Listings','duration_days':14,'price_sle':'0.00','listing_limit':10,'active':True,'description':'14-day trial for testing with up to 10 property or land listings.'})
        self.stdout.write(self.style.SUCCESS(('Created' if created else 'Found')+f' trial plan: {plan.name}'))
