"""URL routes for the inquiries app.

The inquiries app has no public URLs of its own — inquiries are submitted
via the property detail page (``properties.views.detail``). This module is
included from ``config/urls.py`` to keep the app structure consistent, but
exposes no routes.
"""

from django.urls import path  # noqa: F401  (imported for consistency with other urls.py files)

app_name = "inquiries"

urlpatterns = []