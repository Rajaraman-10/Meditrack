from rest_framework.permissions import BasePermission


class HasRole(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.allowed_roles
        )


class IsAdmin(HasRole):
    allowed_roles = ("admin",)


class IsAdminOrReceptionist(HasRole):
    allowed_roles = ("admin", "receptionist")


class IsClinicStaff(HasRole):
    allowed_roles = ("admin", "receptionist", "doctor")


class IsDoctor(HasRole):
    allowed_roles = ("doctor",)


class IsPatient(HasRole):
    allowed_roles = ("patient",)
