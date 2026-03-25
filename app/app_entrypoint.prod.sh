#!/bin/sh

python manage.py migrate

python manage.py collectstatic --noinput

gunicorn config.wsgi --workers 4 --bind 0.0.0.0:8000 --timeout 100 --log-level info
#gunicorn config.asgi:application  -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 4 --log-level info
