from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model. A single table holds both patients and admins; the
    `role` flag is what decides which dashboard they land on and what the
    API will let them do.
    """
    ROLE_CHOICES = (
        ('patient', 'Patient'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"


class Doctor(models.Model):
    """
    A doctor profile attached to a user account. Availability is stored as
    simple comma-separated strings (same approach as Assignment 1) so the
    booking screen can work out which days/slots are on offer.
    """
    DAYS_CHOICES = [
        ('mon', 'Monday'), ('tue', 'Tuesday'), ('wed', 'Wednesday'),
        ('thu', 'Thursday'), ('fri', 'Friday'), ('sat', 'Saturday'), ('sun', 'Sunday'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100)
    available_days = models.CharField(max_length=100)  # stored as "mon,tue,wed"
    slots = models.TextField()                          # stored as "09:30,10:30,11:00"
    created_at = models.DateTimeField(auto_now_add=True)

    def get_days_list(self):
        return self.available_days.split(',') if self.available_days else []

    def get_slots_list(self):
        return self.slots.split(',') if self.slots else []

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} – {self.specialization}"


class Appointment(models.Model):
    """A booking made by a patient against a doctor's date/slot."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    slot = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Database-level guarantee that the same doctor/date/slot can't be
        # taken twice — our last line of defence against double booking.
        unique_together = ('doctor', 'date', 'slot')

    def __str__(self):
        return (
            f"{self.patient.get_full_name()} → "
            f"Dr. {self.doctor.user.get_full_name()} on {self.date} at {self.slot}"
        )
