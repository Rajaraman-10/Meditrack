from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.billing.models import Invoice
from apps.notifications.services import create_notification
from apps.consultations.models import Consultation

from .models import Prescription, PrescriptionItem


def create_prescription(*, consultation, doctor_user, items, instructions=""):
    if consultation.appointment.doctor.user_id != doctor_user.pk:
        raise PermissionDenied("You may only prescribe for your own consultations.")
    if consultation.status not in (
        Consultation.Status.COMPLETED,
    ):
        raise ValidationError(
            "Complete the consultation before issuing a prescription."
        )
    if not items:
        raise ValidationError({"items": "At least one medication is required."})

    with transaction.atomic():
        prescription = Prescription.objects.create(
            consultation=consultation,
            instructions=instructions,
        )
        PrescriptionItem.objects.bulk_create(
            [
                PrescriptionItem(prescription=prescription, **item)
                for item in items
            ]
        )
        record_event(
            actor=doctor_user,
            action="prescription.created",
            instance=prescription,
            metadata={"item_count": len(items)},
        )
        create_notification(
            recipient=consultation.appointment.patient.user,
            title="New prescription",
            message="Your prescription is ready. Payment is required before it can be released.",
            category="prescription",
            target_url="/prescriptions",
        )
        return prescription


def release_prescription(*, prescription_id, actor):
    if actor.role not in ("admin", "billing"):
        raise PermissionDenied("Only billing staff can release prescriptions.")

    with transaction.atomic():
        prescription = (
            Prescription.objects.select_for_update()
            .select_related("consultation__appointment__patient__user")
            .get(pk=prescription_id)
        )
        if prescription.status == Prescription.Status.RELEASED:
            raise ValidationError("This prescription has already been released.")
        try:
            invoice = Invoice.objects.select_for_update().get(
                appointment=prescription.consultation.appointment,
            )
        except Invoice.DoesNotExist as error:
            raise ValidationError(
                "Create and issue an invoice for this appointment before releasing the prescription."
            ) from error
        if invoice.status != Invoice.Status.PAID:
            raise ValidationError(
                "The invoice must be paid before the prescription can be released."
            )

        prescription.status = Prescription.Status.RELEASED
        prescription.released_at = timezone.now()
        prescription.released_by = actor
        prescription.save(
            update_fields=("status", "released_at", "released_by"),
        )
        record_event(
            actor=actor,
            action="prescription.released",
            instance=prescription,
            metadata={"invoice_id": invoice.pk},
        )
        create_notification(
            recipient=prescription.consultation.appointment.patient.user,
            title="Prescription released",
            message="Your payment is confirmed. Your prescription is now available.",
            category="prescription",
            target_url="/prescriptions",
        )
        return prescription
