release: python manage.py collectstatic --noinput && python manage.py migrate
web: gunicorn corvidian.wsgi --bind 0.0.0.0:$PORT
