from django.conf import settings
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        IN_CONSULTATION = "in_consultation", "In Consultation"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        "clinics.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    reason = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_appointments",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("starts_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="appointment_end_after_start",
            ),
        ]
        indexes = [
            models.Index(fields=("doctor", "starts_at", "status")),
            models.Index(fields=("patient", "starts_at")),
        ]

    def __str__(self):
        return f"{self.patient} · {self.starts_at:%Y-%m-%d %H:%M}"


class QueueEntry(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        IN_CONSULTATION = "in_consultation", "In Consultation"
        COMPLETED = "completed", "Completed"
        LEFT = "left", "Left Queue"

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name="queue_entry",
    )
    doctor = models.ForeignKey(
        "clinics.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="queue_entries",
    )
    queue_date = models.DateField()
    position = models.PositiveIntegerField()
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.WAITING,
    )
    checked_in_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "queue_date", "position"),
                name="unique_doctor_queue_position_per_day",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="queue_position_must_be_positive",
            ),
        ]
        indexes = [
            models.Index(fields=("doctor", "queue_date", "status", "position")),
        ]

    def __str__(self):
        return f"{self.doctor} · {self.queue_date} · #{self.position}"
