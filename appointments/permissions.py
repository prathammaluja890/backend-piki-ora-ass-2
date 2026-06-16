from rest_framework.permissions import BasePermission

# Custom permission classes — the API equivalent of the @admin_required /
# @patient_required decorators we used in Assignment 1.


class IsAdmin(BasePermission):
    """Only let logged-in users whose role is 'admin' through."""
    message = "You must be an administrator to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsPatient(BasePermission):
    """Only let logged-in patients through."""
    message = "You must be logged in as a patient to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'patient'
        )
