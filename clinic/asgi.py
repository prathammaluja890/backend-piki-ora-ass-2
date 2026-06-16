"""ASGI config for the clinic project."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')

application = get_asgi_application()
