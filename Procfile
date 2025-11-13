web: python manage.py migrate && python manage.py collectstatic --noinput && PYTHONPATH=mysite gunicorn --chdir mysite mysite.wsgi:application
