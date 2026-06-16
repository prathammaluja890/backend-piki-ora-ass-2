"""
Seed the database with a handful of demo accounts and doctors so the app
is usable straight after setup. Run with:  python manage.py seed
"""

from django.core.management.base import BaseCommand
from appointments.models import User, Doctor


class Command(BaseCommand):
    help = "Populate the database with demo users, doctors and an admin."

    def handle(self, *args, **options):
        # ── Admin account ──
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_user(
                username='admin', email='admin@pikiora.co.nz',
                first_name='Site', last_name='Admin',
                password='admin123', role='admin',
            )
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin (admin / admin123)"))
        else:
            self.stdout.write("Admin already exists, skipping.")

        # ── Demo patient ──
        if not User.objects.filter(username='patient').exists():
            User.objects.create_user(
                username='patient', email='tama@example.com',
                first_name='Tama', last_name='Wirihana',
                password='patient123', role='patient',
            )
            self.stdout.write(self.style.SUCCESS("Created patient (patient / patient123)"))
        else:
            self.stdout.write("Demo patient already exists, skipping.")

        # ── Demo doctors ── (same line-up as the Assignment 1 landing page)
        demo_doctors = [
            {
                'username': 'dr.patel', 'first_name': 'Shreya', 'last_name': 'Patel',
                'email': 'patel@pikiora.co.nz', 'specialization': 'General Practice',
                'available_days': 'mon,tue,wed,thu,fri', 'slots': '09:00,09:30,10:00,10:30,11:00',
            },
            {
                'username': 'dr.liu', 'first_name': 'James', 'last_name': 'Liu',
                'email': 'liu@pikiora.co.nz', 'specialization': 'Cardiology',
                'available_days': 'mon,wed,fri', 'slots': '13:00,13:30,14:00,14:30',
            },
            {
                'username': 'dr.moana', 'first_name': 'Anika', 'last_name': 'Moana',
                'email': 'moana@pikiora.co.nz', 'specialization': 'Paediatrics',
                'available_days': 'tue,thu', 'slots': '10:00,11:00,14:00,15:00',
            },
        ]

        for d in demo_doctors:
            if User.objects.filter(username=d['username']).exists():
                continue
            user = User.objects.create_user(
                username=d['username'], email=d['email'],
                first_name=d['first_name'], last_name=d['last_name'],
                password='doctor123', role='admin',
            )
            Doctor.objects.create(
                user=user, specialization=d['specialization'],
                available_days=d['available_days'], slots=d['slots'],
            )
            self.stdout.write(self.style.SUCCESS(f"Created Dr. {d['first_name']} {d['last_name']}"))

        self.stdout.write(self.style.SUCCESS("\nSeeding complete."))
