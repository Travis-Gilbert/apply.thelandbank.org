web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py ensure_superuser && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 3
