"""App configuration for the users app."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Users"

    def ready(self):
        # Importing the signals module registers the receivers (e.g.
        # ``assign_trial``). Django only imports app modules that are
        # referenced; without this, no signal handler would ever fire.
        # The import is for its side-effects, not for a name.
        from . import signals  # noqa: F401