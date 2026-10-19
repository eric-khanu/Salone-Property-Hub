from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from .models import Plan, Subscription, Payment
from .services import current_subscription
class SubscriptionPolicyTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='owner1',password='strong-password-123',role='owner')
    def test_owner_receives_ten_listing_trial(self):
        sub=current_subscription(self.user,Plan.Kind.LISTING)
        self.assertIsNotNone(sub)
        self.assertEqual(sub.listings_allowed,10)
        self.assertTrue(sub.is_current)
    def test_expired_trial_is_not_current(self):
        sub=Subscription.objects.get(user=self.user,plan__is_trial=True)
        sub.ends_at=timezone.now()-timedelta(seconds=1); sub.save(update_fields=['ends_at'])
        self.assertIsNone(current_subscription(self.user,Plan.Kind.LISTING))
    def test_ad_plan_is_separate_from_listing_plan(self):
        ad_plan=Plan.objects.create(name='Company month',kind=Plan.Kind.AD,duration_days=30,price_sle=500,listing_limit=0)
        self.assertNotEqual(ad_plan.kind,Plan.Kind.LISTING)
