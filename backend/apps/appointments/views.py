from datetime import date

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import PatientProfile

from .models import Appointment, QueueEntry
from .serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    AppointmentUpdateSerializer,
    QueueEntrySerializer,
    QueueEntryUpdateSerializer,
)
from .services import book_appointment, cancel_appointment, check_in_appointment, reschedule_appointment

User = get_user_model()
CLINIC_STAFF_ROLES = (User.Role.ADMIN, User.Role.RECEPTIONIST)


class AppointmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related(
            "patient__user",
            "doctor__user",
            "doctor__department",
        )
        if user.role in CLINIC_STAFF_ROLES:
            pass
        elif user.role == User.Role.DOCTOR:
            queryset = queryset.filter(doctor__user=user)
        elif user.role == User.Role.PATIENT:
            queryset = queryset.filter(patient__user=user)
        else:
            return queryset.none()

        date_filter = self.request.query_params.get("date")
        if date_filter:
            try:
                target_date = date.fromisoformat(date_filter)
            except ValueError as error:
                raise ValidationError({"date": "Use YYYY-MM-DD format."}) from error
            queryset = queryset.filter(
                starts_at__date=target_date,
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentCreateSerializer
        if self.action in ("partial_update", "update"):
            return AppointmentUpdateSerializer
        return AppointmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = book_appointment(
            doctor_id=serializer.validated_data["doctor"].pk,
            starts_at=serializer.validated_data["starts_at"],
            patient=serializer.validated_data["patient"],
            created_by=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        appointment = self.get_object()
        serializer = AppointmentUpdateSerializer(
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        is_staff = request.user.role in CLINIC_STAFF_ROLES
        is_owner = (
            request.user.role == User.Role.PATIENT
            and appointment.patient.user_id == request.user.pk
        )
        if not is_staff and not is_owner:
            raise PermissionDenied("You may not update this appointment.")

        if "doctor" in changes or "starts_at" in changes:
            if not is_staff:
                raise PermissionDenied("Only clinic staff may reschedule appointments.")
            if "doctor" not in changes or "starts_at" not in changes:
                raise ValidationError("Rescheduling requires both doctor and starts_at.")
            appointment = reschedule_appointment(
                appointment_id=appointment.pk,
                doctor_id=changes["doctor"].pk,
                starts_at=changes["starts_at"],
                actor=request.user,
            )
            changes.pop("doctor")
            changes.pop("starts_at")

        if "status" in changes:
            new_status = changes.pop("status")
            if new_status == Appointment.Status.CANCELLED:
                appointment = cancel_appointment(appointment, request.user)
            elif is_staff and new_status in (
                Appointment.Status.CONFIRMED,
                Appointment.Status.NO_SHOW,
            ):
                if appointment.status not in (
                    Appointment.Status.SCHEDULED,
                    Appointment.Status.CONFIRMED,
                ):
                    raise ValidationError(
                        "This appointment cannot change to that status from its current state."
                    )
                if new_status == Appointment.Status.NO_SHOW and appointment.starts_at > timezone.now():
                    raise ValidationError("An appointment cannot be marked no-show before its start time.")
                appointment.status = new_status
                appointment.save(update_fields=("status", "updated_at"))
            else:
                raise PermissionDenied("That appointment status change is not allowed.")

        if changes:
            if not is_staff:
                raise PermissionDenied("Only clinic staff may update the appointment reason.")
            for field, value in changes.items():
                setattr(appointment, field, value)
            appointment.save(update_fields=(*changes.keys(), "updated_at"))

        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request, pk=None):
        if request.user.role not in CLINIC_STAFF_ROLES:
            raise PermissionDenied("Only clinic staff may check in patients.")
        entry = check_in_appointment(self.get_object().pk, request.user)
        return Response(QueueEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class QueueEntryViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        request = self.request
        raw_date = request.query_params.get("date", timezone.localdate().isoformat())
        try:
            target_date = date.fromisoformat(raw_date)
        except ValueError as error:
            raise ValidationError({"date": "Use YYYY-MM-DD format."}) from error

        queryset = QueueEntry.objects.select_related(
            "doctor__user",
            "appointment__patient__user",
        ).filter(queue_date=target_date)
        if request.user.role == User.Role.DOCTOR:
            queryset = queryset.filter(doctor__user=request.user)
        elif request.user.role == User.Role.PATIENT:
            queryset = queryset.filter(appointment__patient__user=request.user)
        elif request.user.role not in CLINIC_STAFF_ROLES:
            raise PermissionDenied("You may not view the waiting queue.")

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def get_serializer_class(self):
        if self.action == "partial_update":
            return QueueEntryUpdateSerializer
        return QueueEntrySerializer

    def partial_update(self, request, *args, **kwargs):
        if request.user.role not in CLINIC_STAFF_ROLES:
            raise PermissionDenied("Only receptionists or administrators can manage the queue.")
        entry = self.get_object()
        serializer = self.get_serializer(entry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if new_status not in (QueueEntry.Status.WAITING, QueueEntry.Status.LEFT):
            raise ValidationError("Reception may set a queue entry to waiting or left.")
        serializer.save()
        return Response(QueueEntrySerializer(entry).data)


class PatientAppointmentHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, patient_id):
        user = request.user
        if user.role == User.Role.PATIENT:
            profile = PatientProfile.objects.filter(user=user).first()
            if not profile or profile.pk != patient_id:
                raise PermissionDenied("You may only view your own appointment history.")
        elif user.role not in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            raise PermissionDenied("You may not view this patient's appointment history.")
        queryset = Appointment.objects.filter(patient_id=patient_id).select_related(
            "patient__user",
            "doctor__user",
            "doctor__department",
        )
        return Response(AppointmentSerializer(queryset, many=True).data)
