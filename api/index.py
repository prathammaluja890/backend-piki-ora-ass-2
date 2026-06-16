import os
from django.core.wsgi import get_wsgi_application

# Entry point Vercel's Python runtime looks for. It just hands off to Django.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic.settings')

app = get_wsgi_application()
