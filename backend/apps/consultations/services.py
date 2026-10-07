from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.appointments.models import Appointment, QueueEntry
from apps.audit.services import record_event
from apps.notifications.services import create_notification

from .models import Consultation


def start_consultation(*, appointment_id, doctor_user):
    with transaction.atomic():
        appointment = (
            Appointment.objects.select_for_update()
            .select_related("doctor__user", "patient__user")
            .filter(pk=appointment_id)
            .first()
        )
        if not appointment:
            raise NotFound("Appointment not found.")
        if appointment.doctor.user_id != doctor_user.pk:
            raise PermissionDenied("You may only start consultations for your appointments.")
        if appointment.status != Appointment.Status.CHECKED_IN:
            raise ValidationError("Only checked-in appointments can start a consultation.")
        if hasattr(appointment, "consultation"):
            raise ValidationError("A consultation already exists for this appointment.")

        consultation = Consultation.objects.create(appointment=appointment)
        appointment.status = Appointment.Status.IN_CONSULTATION
        appointment.save(update_fields=("status", "updated_at"))
        QueueEntry.objects.filter(
            appointment=appointment,
            status=QueueEntry.Status.WAITING,
        ).update(status=QueueEntry.Status.IN_CONSULTATION)
        record_event(
            actor=doctor_user,
            action="consultation.started",
            instance=consultation,
        )
        create_notification(
            recipient=appointment.patient.user,
            title="Consultation started",
            message="Your doctor has started your consultation.",
            category="consultation",
            target_url="/appointments",
        )
        return consultation


def complete_consultation(*, consultation, doctor_user):
    with transaction.atomic():
        consultation = (
            Consultation.objects.select_for_update()
            .select_related("appointment__doctor__user", "appointment__patient__user")
            .get(pk=consultation.pk)
        )
        appointment = Appointment.objects.select_for_update().get(
            pk=consultation.appointment_id
        )
        if appointment.doctor.user_id != doctor_user.pk:
            raise PermissionDenied("You may only complete your own consultations.")
        if consultation.status != Consultation.Status.IN_PROGRESS:
            raise ValidationError("This consultation has already been completed.")
        if not consultation.diagnosis.strip():
            raise ValidationError({"diagnosis": "A diagnosis is required to complete a consultation."})

        consultation.status = Consultation.Status.COMPLETED
        consultation.completed_at = timezone.now()
        consultation.save(update_fields=("status", "completed_at", "updated_at"))
        appointment.status = Appointment.Status.COMPLETED
        appointment.save(update_fields=("status", "updated_at"))
        QueueEntry.objects.filter(
            appointment=appointment,
            status=QueueEntry.Status.IN_CONSULTATION,
        ).update(status=QueueEntry.Status.COMPLETED)
        record_event(
            actor=doctor_user,
            action="consultation.completed",
            instance=consultation,
        )
        create_notification(
            recipient=appointment.patient.user,
            title="Consultation completed",
            message="Your consultation is complete. Visit your account for the latest records.",
            category="consultation",
            target_url="/consultations",
        )
        return consultation
