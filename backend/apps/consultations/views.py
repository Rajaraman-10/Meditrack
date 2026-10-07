from django.contrib.auth import get_user_model
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit.services import record_event
from apps.notifications.services import create_notification

from .models import Consultation, ConsultationNote
from .serializers import (
    ConsultationNoteCreateSerializer,
    ConsultationNoteSerializer,
    ConsultationSerializer,
    ConsultationStartSerializer,
)
from .services import complete_consultation, start_consultation

User = get_user_model()


class ConsultationViewSet(
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
        queryset = Consultation.objects.select_related(
            "appointment__patient__user",
            "appointment__doctor__user",
        ).prefetch_related("notes")
        if user.role == User.Role.ADMIN:
            return queryset
        if user.role == User.Role.DOCTOR:
            return queryset.filter(appointment__doctor__user=user)
        if user.role == User.Role.PATIENT:
            return queryset.filter(appointment__patient__user=user)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return ConsultationStartSerializer
        return ConsultationSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.DOCTOR:
            raise PermissionDenied("Only the assigned doctor can start a consultation.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consultation = start_consultation(
            appointment_id=serializer.validated_data["appointment"],
            doctor_user=request.user,
        )
        return Response(
            ConsultationSerializer(consultation).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        consultation = self.get_object()
        if (
            request.user.role != User.Role.DOCTOR
            or consultation.appointment.doctor.user_id != request.user.pk
        ):
            raise PermissionDenied("Only the assigned doctor may update clinical notes.")
        if consultation.status != Consultation.Status.IN_PROGRESS:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Completed consultation notes cannot be edited.")
        serializer = ConsultationSerializer(
            consultation,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        for field in ("diagnosis", "clinical_notes", "follow_up_date"):
            if field in serializer.validated_data:
                setattr(consultation, field, serializer.validated_data[field])
        consultation.save(update_fields=("diagnosis", "clinical_notes", "follow_up_date", "updated_at"))
        record_event(
            actor=request.user,
            action="consultation.notes_updated",
            instance=consultation,
        )
        create_notification(
            recipient=consultation.appointment.patient.user,
            title="Clinical record updated",
            message="Your doctor updated your consultation record.",
            category="consultation",
            target_url="/consultations",
        )
        return Response(ConsultationSerializer(consultation).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        consultation = self.get_object()
        if request.user.role != User.Role.DOCTOR:
            raise PermissionDenied("Only a doctor can complete a consultation.")
        consultation = complete_consultation(
            consultation=consultation,
            doctor_user=request.user,
        )
        return Response(ConsultationSerializer(consultation).data)

    @action(detail=True, methods=["post"], url_path="notes")
    def add_note(self, request, pk=None):
        consultation = self.get_object()
        if (
            request.user.role != User.Role.DOCTOR
            or consultation.appointment.doctor.user_id != request.user.pk
        ):
            raise PermissionDenied("Only the assigned doctor can add a consultation note.")
        if consultation.status != Consultation.Status.IN_PROGRESS:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Completed consultation notes cannot be edited.")
        serializer = ConsultationNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.save(consultation=consultation, author=request.user)
        record_event(actor=request.user, action="consultation.note_added", instance=note)
        return Response(
            ConsultationNoteSerializer(note).data,
            status=status.HTTP_201_CREATED,
        )
