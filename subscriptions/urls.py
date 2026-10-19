"""URL routes for subscription plans and offline payment submission."""

from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    # Plan catalogue (listings + ad placements).
    path("", views.plans, name="plans"),

    # Submit an offline payment for a specific plan.
    path("pay/<int:plan_id>/", views.submit_payment, name="submit_payment"),
]