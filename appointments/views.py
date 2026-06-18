import datetime

from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, Doctor, Appointment
from .permissions import IsAdmin, IsPatient
from .serializers import (
    RegisterSerializer, UserSerializer, PatientUpdateSerializer,
    DoctorSerializer, DoctorCreateSerializer, DoctorUpdateSerializer,
    AppointmentSerializer, AppointmentBookSerializer,
)


# ══════════════════════════════════════════════════════════
#  AUTHENTICATION
# ══════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Public patient sign-up. Returns the new user on success."""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {'message': 'Account created! Please log in.', 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Log in with username + password. We don't use authenticate() here so the
    error message stays the same whether the username or the password is wrong.
    Hands back a token plus the user record (so the frontend knows the role).
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'detail': 'Please provide both a username and a password.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    if user is None or not user.check_password(password):
        return Response(
            {'detail': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # get_or_create means logging in twice reuses the same token.
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Throw away the caller's token so it can't be reused."""
    Token.objects.filter(user=request.user).delete()
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the currently logged-in user — handy for restoring sessions."""
    return Response(UserSerializer(request.user).data)




class DoctorViewSet(viewsets.ModelViewSet):
    """
    Doctors endpoint.

    - Any logged-in user can browse doctors (patients need this to book).
    - Only admins can add, edit or delete them.
    """
    queryset = Doctor.objects.select_related('user').all().order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return DoctorCreateSerializer
        if self.action in ['update', 'partial_update']:
            return DoctorUpdateSerializer
        return DoctorSerializer

    def get_permissions(self):
        # Read actions: any authenticated user. Write actions: admins only.
        if self.action in ['list', 'retrieve', 'availability']:
            return [IsAuthenticated()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        # Optional search by name or specialization (used on both the admin
        # doctor list and the patient "find doctors" screen).
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(specialization__icontains=search)
            )
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        # Respond with the full read representation, not the write one.
        return Response(DoctorSerializer(doctor).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        doctor = self.get_object()
        serializer = self.get_serializer(doctor, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        return Response(DoctorSerializer(doctor).data)

    def destroy(self, request, *args, **kwargs):
        doctor = self.get_object()
        # Don't allow deleting a doctor who still has pending appointments —
        # same guard rail as Assignment 1.
        pending_count = Appointment.objects.filter(doctor=doctor, status='pending').count()
        if pending_count > 0:
            return Response(
                {'detail': f"Cannot delete — this doctor has {pending_count} pending appointment(s)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Deleting the user cascades to the doctor profile.
        doctor.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """
        Work out which dates/slots a doctor has on offer over the next two
        weeks, plus which slots are already taken. The booking screen uses
        this to show only free slots.
        """
        doctor = self.get_object()
        days = doctor.get_days_list()
        today = timezone.now().date()

        available_dates = []
        for i in range(1, 15):  # look 14 days ahead, starting tomorrow
            day = today + datetime.timedelta(days=i)
            day_name = day.strftime('%a').lower()[:3]
            if day_name in days:
                available_dates.append(day.isoformat())

        # Slots already booked (pending) so the UI can grey them out.
        booked = list(
            Appointment.objects.filter(doctor=doctor, status='pending')
            .values('date', 'slot')
        )
        booked = [{'date': b['date'].isoformat(), 'slot': b['slot']} for b in booked]

        return Response({
            'doctor': DoctorSerializer(doctor).data,
            'available_dates': available_dates,
            'slots': doctor.get_slots_list(),
            'booked': booked,
        })


# ══════════════════════════════════════════════════════════
#  APPOINTMENTS
# ══════════════════════════════════════════════════════════

class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Appointments endpoint.

    Patients only ever see (and touch) their own appointments; admins see
    everything. Booking and rescheduling both run the double-booking check.
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related('patient', 'doctor__user')

        if user.role == 'patient':
            qs = qs.filter(patient=user)
        # Admins fall through and see all appointments.

        # Optional filters shared by both the admin and patient lists.
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
                | Q(doctor__user__first_name__icontains=search)
                | Q(doctor__user__last_name__icontains=search)
            )

        status_filter = self.request.query_params.get('status', '').strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.order_by('-date', '-slot')

    def _slot_taken(self, doctor, date, slot, exclude_id=None):
        """Return True if the doctor already has a pending booking there."""
        qs = Appointment.objects.filter(
            doctor=doctor, date=date, slot=slot, status='pending'
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return qs.exists()

    def create(self, request, *args, **kwargs):
        """Patient books a new appointment."""
        if request.user.role != 'patient':
            return Response(
                {'detail': 'Only patients can book appointments.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AppointmentBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.validated_data['doctor']
        date = serializer.validated_data['date']
        slot = serializer.validated_data['slot']

        if self._slot_taken(doctor, date, slot):
            return Response(
                {'detail': 'This slot is already booked. Please choose another.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment = Appointment.objects.create(
            patient=request.user, doctor=doctor, date=date, slot=slot, status='pending',
        )
        # The 201 response doubles as the "booking confirmation" the brief asks for.
        return Response(
            {
                'message': f"Appointment booked with Dr. {doctor.user.get_full_name()} "
                           f"on {date} at {slot}.",
                'appointment': AppointmentSerializer(appointment).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """
        Reschedule an appointment. Patients may only move their own pending
        bookings; admins can edit any appointment.
        """
        appointment = self.get_object()
        user = request.user

        if user.role == 'patient' and appointment.status != 'pending':
            return Response(
                {'detail': 'Only pending appointments can be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date = request.data.get('date', appointment.date)
        slot = request.data.get('slot', appointment.slot)

        if self._slot_taken(appointment.doctor, date, slot, exclude_id=appointment.id):
            return Response(
                {'detail': 'This slot is already booked. Please choose another.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.date = date
        appointment.slot = slot
        appointment.save()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Patient (or admin) cancels an appointment by flagging it cancelled."""
        appointment = self.get_object()

        if request.user.role == 'patient' and appointment.status != 'pending':
            return Response(
                {'detail': 'Only pending appointments can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = 'cancelled'
        appointment.save()
        return Response({
            'message': 'Appointment cancelled successfully.',
            'appointment': AppointmentSerializer(appointment).data,
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def set_status(self, request, pk=None):
        """Admin-only: move an appointment between pending/completed/cancelled."""
        appointment = self.get_object()
        new_status = request.data.get('status')
        if new_status not in ['pending', 'completed', 'cancelled']:
            return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = new_status
        appointment.save()
        return Response({
            'message': f'Appointment status updated to {new_status}.',
            'appointment': AppointmentSerializer(appointment).data,
        })


# ══════════════════════════════════════════════════════════
#  PATIENTS (admin management)
# ══════════════════════════════════════════════════════════

class PatientViewSet(viewsets.ModelViewSet):
    """Admin-only management of patient accounts."""
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'put', 'patch', 'delete']  # no creating patients here

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return PatientUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        qs = User.objects.filter(role='patient').order_by('-date_joined')
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
            )
        return qs

    def update(self, request, *args, **kwargs):
        patient = self.get_object()
        serializer = self.get_serializer(patient, data=request.data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(UserSerializer(patient).data)


# ══════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ══════════════════════════════════════════════════════════

class AdminStatsView(APIView):
    """Headline numbers for the admin dashboard."""
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            'total_doctors': Doctor.objects.count(),
            'total_patients': User.objects.filter(role='patient').count(),
            'total_appointments': Appointment.objects.count(),
            'pending': Appointment.objects.filter(status='pending').count(),
            'completed': Appointment.objects.filter(status='completed').count(),
            'cancelled': Appointment.objects.filter(status='cancelled').count(),
        })


class PatientStatsView(APIView):
    """Headline numbers + next few bookings for the patient dashboard."""
    permission_classes = [IsPatient]

    def get(self, request):
        user = request.user
        upcoming = (
            Appointment.objects.filter(
                patient=user, status='pending', date__gte=timezone.now().date()
            )
            .select_related('doctor__user')
            .order_by('date', 'slot')[:3]
        )
        return Response({
            'total': Appointment.objects.filter(patient=user).count(),
            'pending': Appointment.objects.filter(patient=user, status='pending').count(),
            'completed': Appointment.objects.filter(patient=user, status='completed').count(),
            'upcoming': AppointmentSerializer(upcoming, many=True).data,
        })
