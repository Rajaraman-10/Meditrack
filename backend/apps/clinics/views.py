from datetime import date

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin, IsAdminOrReceptionist

from .models import Department, DoctorAvailability, DoctorProfile, ScheduleException
from .serializers import (
    DepartmentSerializer,
    DoctorAvailabilitySerializer,
    DoctorCreateSerializer,
    DoctorProfileSerializer,
    ScheduleExceptionSerializer,
)
from .services import get_slots_for_date

User = get_user_model()


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role != User.Role.ADMIN:
            return queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.filter(user__is_active=True).select_related(
        "user", "department"
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.ADMIN:
            return queryset
        return queryset.filter(department__is_active=True)

    def get_serializer_class(self):
        if self.action == "create":
            return DoctorCreateSerializer
        return DoctorProfileSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.save()
        return Response(
            DoctorProfileSerializer(doctor).data,
            status=status.HTTP_201_CREATED,
        )


class DoctorAvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorAvailabilitySerializer
    queryset = DoctorAvailability.objects.select_related("doctor", "doctor__user")

    def get_queryset(self):
        queryset = super().get_queryset()
        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        if self.request.user.role == User.Role.DOCTOR:
            queryset = queryset.filter(doctor__user=self.request.user)
        return queryset

    def _check_schedule_permission(self, doctor_id):
        user = self.request.user
        if user.role == User.Role.DOCTOR:
            if not DoctorProfile.objects.filter(pk=doctor_id, user=user).exists():
                raise PermissionDenied("Doctors may only manage their own schedule.")
        elif user.role not in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            raise PermissionDenied("Only clinic staff may manage doctor schedules.")

    def perform_create(self, serializer):
        self._check_schedule_permission(serializer.validated_data["doctor"].pk)
        serializer.save()

    def perform_update(self, serializer):
        doctor = serializer.validated_data.get("doctor", self.get_object().doctor)
        self._check_schedule_permission(doctor.pk)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_schedule_permission(instance.doctor_id)
        instance.delete()


class ScheduleExceptionViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleExceptionSerializer
    queryset = ScheduleException.objects.select_related("doctor", "doctor__user")

    def get_queryset(self):
        queryset = super().get_queryset()
        doctor_id = self.request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        if self.request.user.role == User.Role.DOCTOR:
            queryset = queryset.filter(doctor__user=self.request.user)
        return queryset

    def _check_schedule_permission(self, doctor_id):
        if self.request.user.role == User.Role.DOCTOR:
            if not DoctorProfile.objects.filter(
                pk=doctor_id, user=self.request.user
            ).exists():
                raise PermissionDenied("Doctors may only manage their own schedule.")
        elif self.request.user.role not in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            raise PermissionDenied("Only clinic staff may manage schedule exceptions.")

    def perform_create(self, serializer):
        self._check_schedule_permission(serializer.validated_data["doctor"].pk)
        serializer.save()

    def perform_update(self, serializer):
        doctor = serializer.validated_data.get("doctor", self.get_object().doctor)
        self._check_schedule_permission(doctor.pk)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_schedule_permission(instance.doctor_id)
        instance.delete()


class DoctorSlotsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, doctor_id):
        raw_date = request.query_params.get("date")
        if not raw_date:
            raise ValidationError({"date": "This query parameter is required (YYYY-MM-DD)."})
        try:
            target_date = date.fromisoformat(raw_date)
        except ValueError as error:
            raise ValidationError({"date": "Use YYYY-MM-DD format."}) from error

        doctor = get_object_or_404(
            DoctorProfile.objects.select_related("user", "department"),
            pk=doctor_id,
            user__is_active=True,
            department__is_active=True,
        )
        slots = get_slots_for_date(doctor, target_date)
        return Response(
            {
                "doctor_id": doctor.pk,
                "date": target_date.isoformat(),
                "timezone": str(timezone.get_default_timezone()),
                "slot_duration_minutes": doctor.slot_duration_minutes,
                "slots": [slot.isoformat() for slot in slots],
            }
        )
