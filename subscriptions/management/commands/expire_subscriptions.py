from django.core.management.base import BaseCommand
from subscriptions.services import expire_subscriptions
class Command(BaseCommand):
    help='Expire subscriptions and hide listings whose plan has ended.'
    def handle(self,*args,**options):
        expire_subscriptions(); self.stdout.write(self.style.SUCCESS('Expired subscriptions and listings updated.'))
