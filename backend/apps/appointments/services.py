from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.clinics.models import DoctorProfile
from apps.clinics.services import ACTIVE_APPOINTMENT_STATUSES, get_slots_for_date
from apps.notifications.services import create_notification
from apps.patients.models import PatientProfile

from .models import Appointment, QueueEntry

User = get_user_model()


class BookingConflict(APIException):
    status_code = 409
    default_detail = "That appointment slot is no longer available."
    default_code = "booking_conflict"


def _doctor_locked(doctor_id):
    return DoctorProfile.objects.select_for_update().get(
        pk=doctor_id,
        user__is_active=True,
        department__is_active=True,
        is_accepting_appointments=True,
    )


def _require_slot(doctor, starts_at):
    local_start = timezone.localtime(starts_at, timezone.get_default_timezone())
    if starts_at <= timezone.now():
        raise ValidationError({"starts_at": "Appointments must be booked in the future."})

    available_slots = get_slots_for_date(doctor, local_start.date())
    if not any(slot == starts_at for slot in available_slots):
        raise BookingConflict()


def book_appointment(*, doctor_id, starts_at, patient, created_by, reason=""):
    with transaction.atomic():
        try:
            doctor = _doctor_locked(doctor_id)
        except DoctorProfile.DoesNotExist as error:
            raise NotFound("This doctor is not currently accepting appointments.") from error

        _require_slot(doctor, starts_at)
        ends_at = starts_at + timedelta(minutes=doctor.slot_duration_minutes)
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            starts_at=starts_at,
            ends_at=ends_at,
            reason=reason,
            created_by=created_by,
        )
        record_event(
            actor=created_by,
            action="appointment.created",
            instance=appointment,
        )
        create_notification(
            recipient=patient.user,
            title="Appointment booked",
            message="Your appointment has been scheduled.",
            category="appointment",
            target_url="/appointments",
        )
        return appointment


def reschedule_appointment(*, appointment_id, doctor_id, starts_at, actor):
    initial = Appointment.objects.filter(pk=appointment_id).values(
        "doctor_id", "starts_at", "ends_at"
    ).first()
    if not initial:
        raise NotFound("Appointment not found.")
    if initial["doctor_id"] == doctor_id and initial["starts_at"] == starts_at:
        raise ValidationError("The appointment already uses this slot.")

    doctor_ids = sorted({initial["doctor_id"], doctor_id})
    with transaction.atomic():
        locked_doctors = {
            doctor.pk: doctor
            for doctor in DoctorProfile.objects.select_for_update()
            .filter(pk__in=doctor_ids)
            .order_by("pk")
        }
        appointment = Appointment.objects.select_for_update().filter(
            pk=appointment_id
        ).first()
        if not appointment:
            raise NotFound("Appointment not found.")
        if appointment.status not in (
            Appointment.Status.SCHEDULED,
            Appointment.Status.CONFIRMED,
        ):
            raise ValidationError("Only scheduled or confirmed appointments can be rescheduled.")
        if appointment.doctor_id != initial["doctor_id"]:
            raise BookingConflict()

        doctor = locked_doctors.get(doctor_id)
        if (
            not doctor
            or not doctor.is_accepting_appointments
            or not doctor.user.is_active
            or not doctor.department.is_active
        ):
            raise NotFound("This doctor is not currently accepting appointments.")

        _require_slot(doctor, starts_at)
        appointment.doctor = doctor
        appointment.starts_at = starts_at
        appointment.ends_at = starts_at + timedelta(minutes=doctor.slot_duration_minutes)
        appointment.save(update_fields=("doctor", "starts_at", "ends_at", "updated_at"))
        record_event(
            actor=actor,
            action="appointment.rescheduled",
            instance=appointment,
        )
        create_notification(
            recipient=appointment.patient.user,
            title="Appointment rescheduled",
            message="Your appointment time has changed.",
            category="appointment",
            target_url="/appointments",
        )
        return appointment


def cancel_appointment(appointment, actor):
    if appointment.status not in (
        Appointment.Status.SCHEDULED,
        Appointment.Status.CONFIRMED,
    ):
        raise ValidationError("Only scheduled or confirmed appointments can be cancelled.")
    if actor.role == User.Role.PATIENT and appointment.patient.user_id != actor.pk:
        raise PermissionDenied("You may only cancel your own appointment.")
    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=("status", "updated_at"))
    record_event(actor=actor, action="appointment.cancelled", instance=appointment)
    create_notification(
        recipient=appointment.patient.user,
        title="Appointment cancelled",
        message="Your appointment has been cancelled.",
        category="appointment",
        target_url="/appointments",
    )
    return appointment


def check_in_appointment(appointment_id, actor):
    initial = Appointment.objects.filter(pk=appointment_id).values(
        "doctor_id"
    ).first()
    if not initial:
        raise NotFound("Appointment not found.")

    with transaction.atomic():
        doctor = DoctorProfile.objects.select_for_update().filter(
            pk=initial["doctor_id"]
        ).first()
        if not doctor:
            raise NotFound("Appointment doctor not found.")
        appointment = Appointment.objects.select_for_update().filter(
            pk=appointment_id
        ).first()
        if not appointment:
            raise NotFound("Appointment not found.")
        if appointment.doctor_id != doctor.pk:
            raise BookingConflict()
        local_date = timezone.localtime(
            appointment.starts_at,
            timezone.get_default_timezone(),
        ).date()
        if local_date != timezone.localdate():
            raise ValidationError("Patients can only be checked in on the appointment date.")
        if appointment.status not in (
            Appointment.Status.SCHEDULED,
            Appointment.Status.CONFIRMED,
        ):
            raise ValidationError("This appointment cannot be checked in from its current status.")

        position = (
            QueueEntry.objects.filter(doctor=doctor, queue_date=local_date)
            .aggregate(max_position=Max("position"))["max_position"]
            or 0
        ) + 1
        entry = QueueEntry.objects.create(
            appointment=appointment,
            doctor=doctor,
            queue_date=local_date,
            position=position,
        )
        appointment.status = Appointment.Status.CHECKED_IN
        appointment.save(update_fields=("status", "updated_at"))
        record_event(
            actor=actor,
            action="appointment.checked_in",
            instance=appointment,
        )
        return entry
