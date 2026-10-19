"""
WSGI entry point for SL Property Hub.

Used by production servers (gunicorn, uWSGI, mod_wsgi, ...) — NOT by
``python manage.py runserver``, which uses ``config/asgi.py`` or the
built-in WSGI handler depending on the ``--async`` flag.

Example gunicorn command:
    gunicorn config.wsgi:application --bind 0.0.0.0:8000
"""

import os

from django.core.wsgi import get_wsgi_application

# ``setdefault`` (not direct assignment) so hosting platforms can inject
# their own ``DJANGO_SETTINGS_MODULE`` without being overwritten.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Every WSGI server looks for a callable named ``application`` at module
# scope — do not rename this variable.
application = get_wsgi_application()