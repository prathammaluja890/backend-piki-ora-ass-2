from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, Doctor, Appointment


# ── USER / AUTH SERIALIZERS ───────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    """Handles new patient sign-ups (mirrors the old PatientRegistrationForm)."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email',
            'date_of_birth', 'password', 'confirm_password',
        ]

    def validate(self, data):
        # password and cofirm password should same
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')

        # Everyone who registers through the public form is a patient.
        user = User(role='patient', **validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Read-only-ish view of a user, used by /auth/me and patient lists."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'date_of_birth', 'role',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()


class PatientUpdateSerializer(serializers.ModelSerializer):
    """Lets an admin edit a patient, optionally resetting their password."""
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'date_of_birth', 'password']

    def validate_email(self, value):
        # Email must stay unique, but ignore the patient we're currently editing.
        qs = User.objects.filter(email=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        # Only touch the password if a new one was actually supplied.
        if password:
            instance.set_password(password)
        instance.save()
        return instance


# ── DOCTOR SERIALIZERS ────────────────────────────────────

class DoctorSerializer(serializers.ModelSerializer):
    """
    Read serializer for doctors. Flattens the linked user's details and
    splits the CSV fields into proper lists so React doesn't have to.
    """
    full_name = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    days_list = serializers.SerializerMethodField()
    slots_list = serializers.SerializerMethodField()
    total_slots = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'first_name', 'last_name', 'username', 'email',
            'specialization', 'available_days', 'slots',
            'days_list', 'slots_list', 'total_slots', 'created_at',
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    def get_days_list(self, obj):
        return obj.get_days_list()

    def get_slots_list(self, obj):
        return obj.get_slots_list()

    def get_total_slots(self, obj):
        return len(obj.get_slots_list())


class DoctorCreateSerializer(serializers.Serializer):
    """
    Write serializer for adding a doctor. Like Assignment 1, this creates
    both the User account and the Doctor profile in one go.
    """
    # User fields
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    # Doctor fields
    specialization = serializers.CharField(max_length=100)
    available_days = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    slots = serializers.CharField()  # comma separated, e.g. "09:30,10:30"

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        # Doctors get the 'admin' role so they can log into the admin side,
        # exactly as in Assignment 1.
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            date_of_birth=validated_data.get('date_of_birth'),
            role='admin',
        )
        doctor = Doctor.objects.create(
            user=user,
            specialization=validated_data['specialization'],
            available_days=','.join(validated_data['available_days']),
            slots=validated_data['slots'].replace(' ', ''),
        )
        return doctor


class DoctorUpdateSerializer(serializers.Serializer):
    """Update a doctor's availability (days + slots)."""
    available_days = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    slots = serializers.CharField()

    def update(self, instance, validated_data):
        instance.available_days = ','.join(validated_data['available_days'])
        instance.slots = validated_data['slots'].replace(' ', '')
        instance.save()
        return instance


# ── APPOINTMENT SERIALIZERS ───────────────────────────────

class AppointmentSerializer(serializers.ModelSerializer):
    """Read serializer with friendly nested details for the UI."""
    doctor_name = serializers.SerializerMethodField()
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.CharField(source='patient.email', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'doctor', 'doctor_name', 'doctor_specialization',
            'patient', 'patient_name', 'patient_email',
            'date', 'slot', 'status', 'created_at',
        ]

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name()

    def get_patient_name(self, obj):
        return obj.patient.get_full_name()


class AppointmentBookSerializer(serializers.Serializer):
    """Used by patients to book or reschedule an appointment."""
    doctor = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.all())
    date = serializers.DateField()
    slot = serializers.CharField(max_length=10)
