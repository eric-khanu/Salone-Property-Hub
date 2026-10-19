web: python manage.py migrate --run-syncdb && python manage.py seed_plans && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
