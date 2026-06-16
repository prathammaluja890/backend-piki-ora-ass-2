from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # We keep the Django admin enabled for our own convenience during
    # development, but the marked "administrator dashboard" lives entirely
    # in React and talks to the API below — never the built-in admin site.
    path('django-admin/', admin.site.urls),

    # Everything the React app uses sits under /api/.
    path('api/', include('appointments.urls')),
]
