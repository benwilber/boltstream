web: bin/boot gunicorn --bind=127.0.0.1:$PORT --workers=4 --max-requests=1024 --access-logfile=- --error-logfile=- boltstream.wsgi:application
worker: bin/boot celery --app=boltstream worker --loglevel=INFO --concurrency=4
