from django.conf import settings
from django.db import models


class LabTest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    consultation = models.ForeignKey(
        "consultations.Consultation",
        on_delete=models.PROTECT,
        related_name="lab_tests",
    )
    name = models.CharField(max_length=180)
    clinical_question = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_lab_tests",
    )

    class Meta:
        ordering = ("-requested_at",)


class LabReport(models.Model):
    test = models.ForeignKey(
        LabTest,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    result_text = models.TextField(blank=True)
    document = models.ForeignKey(
        "documents.MedicalDocument",
        on_delete=models.PROTECT,
        related_name="lab_reports",
        null=True,
        blank=True,
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lab_reports",
    )
    reported_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-reported_at",)

