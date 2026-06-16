from django.contrib import admin
from .models import User, Doctor, Appointment

# These registrations are only for our own debugging via /django-admin/.
# The marked administrator dashboard is built in React, not here.
admin.site.register(User)
admin.site.register(Doctor)
admin.site.register(Appointment)
