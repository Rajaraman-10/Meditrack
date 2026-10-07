from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.appointments.models import Appointment
from apps.audit.services import record_event
from apps.notifications.services import create_notification

from .models import Invoice, InvoiceItem


def _staff_only(actor):
    if actor.role not in ("admin", "receptionist", "billing"):
        raise PermissionDenied("Only administrators and billing staff can manage invoices.")


def create_invoice(*, appointment, actor, items, currency="INR", discount_amount=Decimal("0.00")):
    _staff_only(actor)
    if appointment.status not in (Appointment.Status.IN_CONSULTATION, Appointment.Status.COMPLETED):
        raise ValidationError("An invoice can be created only after consultation has started.")
    if not items:
        raise ValidationError({"items": "An invoice must contain at least one item."})
    subtotal = sum(
        (
            item["quantity"] * item["unit_price"]
            for item in items
        ),
        start=Decimal("0.00"),
    )
    if discount_amount > subtotal:
        raise ValidationError({"discount_amount": "Discount cannot exceed the invoice subtotal."})
    with transaction.atomic():
        invoice = Invoice.objects.create(
            appointment=appointment,
            created_by=actor,
            currency=currency.upper(),
            discount_amount=discount_amount,
        )
        InvoiceItem.objects.bulk_create(
            [InvoiceItem(invoice=invoice, **item) for item in items]
        )
        record_event(actor=actor, action="invoice.created", instance=invoice)
        return invoice


def change_invoice_status(
    *,
    invoice,
    actor,
    status,
    payment_method=None,
    transaction_reference="",
):
    _staff_only(actor)
    allowed = {
        Invoice.Status.DRAFT: {Invoice.Status.ISSUED, Invoice.Status.VOID},
        Invoice.Status.ISSUED: {Invoice.Status.PAID, Invoice.Status.VOID},
        Invoice.Status.PAID: set(),
        Invoice.Status.VOID: set(),
    }
    if status not in allowed[invoice.status]:
        raise ValidationError("That invoice status transition is not allowed.")
    if status == Invoice.Status.ISSUED and not invoice.items.exists():
        raise ValidationError("Add invoice items before issuing the invoice.")
    if status == Invoice.Status.PAID and not payment_method:
        raise ValidationError({"payment_method": "Choose how the patient paid."})

    invoice.status = status
    update_fields = ["status", "updated_at"]
    if status == Invoice.Status.ISSUED:
        invoice.issued_at = timezone.now()
        update_fields.append("issued_at")
    if status == Invoice.Status.PAID:
        invoice.paid_at = timezone.now()
        update_fields.append("paid_at")
        invoice.payment_method = payment_method
        invoice.transaction_reference = transaction_reference
        update_fields.extend(("payment_method", "transaction_reference"))
    invoice.save(update_fields=update_fields)
    record_event(
        actor=actor,
        action=f"invoice.{status}",
        instance=invoice,
    )
    if status == Invoice.Status.ISSUED:
        create_notification(
            recipient=invoice.appointment.patient.user,
            title="New invoice",
            message="An invoice is ready in your patient account.",
            category="billing",
            target_url="/billing",
        )
    return invoice
