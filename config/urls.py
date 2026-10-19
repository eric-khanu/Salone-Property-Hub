"""
URL configuration for SL Property Hub.

Notes
-----
* Every ``include()`` prefix ends with a trailing slash.
* Root ``''`` catch-all must stay last among root-level paths so it
  doesn't shadow ``robots.txt`` / ``sitemap.xml`` style routes you add later.
* Static/media files are only served by Django when ``DEBUG = True``.
  In production, your web server (nginx/caddy) serves them.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from properties.views import home

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Public
    path("", home, name="home"),

    # App includes (each app defines ``app_name`` in its own urls.py)
    path("accounts/", include("users.urls")),
    path("properties/", include("properties.urls")),
    path("subscriptions/", include("subscriptions.urls")),
    path("advertise/", include("advertisements.urls")),
    path("inquiries/", include("inquiries.urls")),
    path("dashboard/", include("dashboard.urls")),
]

# ---------------------------------------------------------------------------
# Dev-only: serve uploaded media files through Django
# ---------------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ---------------------------------------------------------------------------
# Custom error handlers (uncomment + create views if you want branded pages)
# ---------------------------------------------------------------------------
# handler404 = "config.views.custom_404"
# handler500 = "config.views.custom_500"