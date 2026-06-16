"""WSGI config for the clinic project."""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')

application = get_wsgi_application()

# Vercel looks for a module-level `app` callable.
app = application
