web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn railway_wsgi:application --bind 0.0.0.0:8080
