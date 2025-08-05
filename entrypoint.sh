#!/bin/sh
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 -k eventlet app:app
