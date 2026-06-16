#!/bin/bash
# Build step Vercel runs for the backend: install deps and collect static files
# (so the Django admin and DRF browsable API have their CSS in production).
pip install -r requirements.txt
python manage.py collectstatic --noinput
