from datetime import datetime, timedelta

from django.utils import timezone

from apps.appointments.models import Appointment

from .models import DoctorAvailability, ScheduleException

ACTIVE_APPOINTMENT_STATUSES = (
    Appointment.Status.SCHEDULED,
    Appointment.Status.CONFIRMED,
    Appointment.Status.CHECKED_IN,
    Appointment.Status.IN_CONSULTATION,
)


def get_slots_for_date(doctor, target_date):
    if (
        not doctor.is_accepting_appointments
        or not doctor.department.is_active
        or not doctor.user.is_active
    ):
        return []

    exception = ScheduleException.objects.filter(
        doctor=doctor,
        date=target_date,
    ).first()
    if exception:
        if exception.is_closed:
            return []
        windows = [(exception.start_time, exception.end_time)]
    else:
        windows = list(
            DoctorAvailability.objects.filter(
                doctor=doctor,
                weekday=target_date.weekday(),
                is_active=True,
            ).values_list("start_time", "end_time")
        )

    clinic_timezone = timezone.get_default_timezone()
    slot_length = timedelta(minutes=doctor.slot_duration_minutes)
    candidates = []
    for start_time, end_time in windows:
        cursor = timezone.make_aware(
            datetime.combine(target_date, start_time),
            clinic_timezone,
        )
        window_end = timezone.make_aware(
            datetime.combine(target_date, end_time),
            clinic_timezone,
        )
        while cursor + slot_length <= window_end:
            slot_end = cursor + slot_length
            if cursor > timezone.now():
                candidates.append((cursor, slot_end))
            cursor = slot_end

    if not candidates:
        return []

    first_start = min(start for start, _ in candidates)
    last_end = max(end for _, end in candidates)
    booked = Appointment.objects.filter(
        doctor=doctor,
        status__in=ACTIVE_APPOINTMENT_STATUSES,
        starts_at__lt=last_end,
        ends_at__gt=first_start,
    ).values_list("starts_at", "ends_at")
    booked_intervals = tuple(booked)

    return [
        start
        for start, end in candidates
        if not any(existing_start < end and existing_end > start
                   for existing_start, existing_end in booked_intervals)
    ]
