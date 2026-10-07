from django.conf import settings
from django.db import models


class Consultation(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="consultation",
    )
    diagnosis = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    follow_up_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-started_at",)
        indexes = [models.Index(fields=("status", "follow_up_date"))]

    @property
    def doctor(self):
        return self.appointment.doctor

    @property
    def patient(self):
        return self.appointment.patient

    def __str__(self):
        return f"Consultation for appointment {self.appointment_id}"


class ConsultationNote(models.Model):
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultation_notes",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

