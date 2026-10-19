"""Auth routes: register, login, logout."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register, name="register"),

    # LoginView
    #   - Uses the default ``next`` field so ?next=/dashboard/ works after login.
    #   - ``redirect_authenticated_user=True`` sends already-logged-in users
    #     away from the login form (change to False if you want "switch account").
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="users/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),

    # LogoutView
    #   - Since Django 5.0 this requires POST (GET returns 405).
    #     Templates must <form method="post" action="{% url 'users:logout' %}">.
    #   - ``next_page="home"`` uses LOGOUT_REDIRECT_URL from settings.
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="home"),
        name="logout",
    ),
]