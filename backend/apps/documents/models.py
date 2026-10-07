from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


def medical_document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"medical_documents/{instance.patient_id}/{uuid4().hex}{extension}"


def validate_medical_document(file):
    extension = Path(file.name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError("Only PDF, JPG, JPEG, and PNG files are allowed.")
    if file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError("Medical documents must be 10 MB or smaller.")


class MedicalDocument(models.Model):
    patient = models.ForeignKey(
        "patients.PatientProfile",
        on_delete=models.PROTECT,
        related_name="medical_documents",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.PROTECT,
        related_name="medical_documents",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=80, default="other")
    file = models.FileField(
        upload_to=medical_document_upload_path,
        validators=[validate_medical_document],
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_medical_documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)
        indexes = [models.Index(fields=("patient", "uploaded_at"))]

