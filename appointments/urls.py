from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Routers wire up the standard list/retrieve/create/update/destroy routes
# for our viewsets, plus the custom @action endpoints.
router = DefaultRouter()
router.register(r'doctors', views.DoctorViewSet, basename='doctor')
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')
router.register(r'patients', views.PatientViewSet, basename='patient')

urlpatterns = [
    # ── Auth ──
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/me/', views.me, name='me'),

    # ── Dashboard stats ──
    path('admin/stats/', views.AdminStatsView.as_view(), name='admin_stats'),
    path('patient/stats/', views.PatientStatsView.as_view(), name='patient_stats'),

    # ── Resources (doctors / appointments / patients) ──
    path('', include(router.urls)),
]
