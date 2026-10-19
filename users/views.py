"""User registration view."""

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegisterForm


def register(request):
    """Create a new account, log the user in, and send them to their workspace."""
    # Already authenticated? There's nothing to register for.
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()

        # Explicit backend avoids a ValueError when multiple auth backends
        # are configured (Django requires the argument in that case).
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

        messages.success(
            request,
            "Welcome to SL Property Hub! Complete your profile or start "
            "exploring listings.",
        )

        # Where to go next: the dashboard by default, or a validated `next` URL
        # so a user redirected from a protected page lands where they intended.
        next_url = request.GET.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)
        return redirect("dashboard:home")

    return render(request, "users/register.html", {"form": form})