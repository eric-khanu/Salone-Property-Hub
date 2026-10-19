"""URL routes for property listings."""

from django.urls import path

from . import views

app_name = "properties"

urlpatterns = [
    # Management routes — must come BEFORE the <slug:slug> catch-all below,
    # otherwise e.g. /properties/add/ would match the detail view with slug="add".
    path("add/", views.create, name="create"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("photos/<int:pk>/delete/", views.delete_image, name="delete_image"),

    # Public detail page (catch-all — keep last).
    path("<slug:slug>/", views.detail, name="detail"),
]