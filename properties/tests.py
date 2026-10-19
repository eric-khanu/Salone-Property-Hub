from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from subscriptions.services import current_subscription
from subscriptions.models import Plan
class ListingAccessTests(TestCase):
    def test_anonymous_visitor_can_browse_home(self):
        response=self.client.get(reverse('home'))
        self.assertEqual(response.status_code,200)
    def test_owner_without_active_subscription_is_redirected_to_plans(self):
        user=get_user_model().objects.create_user(username='expired-owner',password='strong-password-123',role='owner')
        sub=current_subscription(user,Plan.Kind.LISTING)
        sub.ends_at=sub.ends_at.replace(year=sub.ends_at.year-1); sub.save(update_fields=['ends_at'])
        self.client.force_login(user)
        response=self.client.get(reverse('properties:create'))
        self.assertRedirects(response,reverse('subscriptions:plans'))
