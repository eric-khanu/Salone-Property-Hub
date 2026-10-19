#!/bin/sh
set -eu
python manage.py makemigrations users properties subscriptions advertisements inquiries dashboard --noinput
python manage.py migrate --run-syncdb --noinput
python manage.py seed_plans
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-3}" --timeout 60 --access-logfile - --error-logfile -
