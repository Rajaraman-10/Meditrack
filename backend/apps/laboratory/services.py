from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.consultations.models import Consultation
from apps.notifications.services import create_notification

from .models import LabReport, LabTest


def _can_manage(consultation, actor):
    return actor.role == "admin" or consultation.appointment.doctor.user_id == actor.pk


def request_lab_test(*, consultation, actor, name, clinical_question=""):
    if not _can_manage(consultation, actor):
        raise PermissionDenied("Only the assigned doctor may request a lab test.")
    if consultation.status != Consultation.Status.IN_PROGRESS:
        raise ValidationError("Tests can only be requested during an active consultation.")
    test = LabTest.objects.create(
        consultation=consultation,
        requested_by=actor,
        name=name,
        clinical_question=clinical_question,
    )
    record_event(actor=actor, action="lab_test.requested", instance=test)
    return test


def record_lab_report(*, test, actor, result_text, document=None):
    if not _can_manage(test.consultation, actor):
        raise PermissionDenied("Only the assigned doctor or an administrator may record results.")
    if test.status == LabTest.Status.CANCELLED:
        raise ValidationError("A cancelled test cannot receive a result.")
    with transaction.atomic():
        report = LabReport.objects.create(
            test=test,
            reported_by=actor,
            result_text=result_text,
            document=document,
        )
        test.status = LabTest.Status.COMPLETED
        test.save(update_fields=("status",))
        record_event(actor=actor, action="lab_report.recorded", instance=report)
        create_notification(
            recipient=test.consultation.appointment.patient.user,
            title="Lab results available",
            message=f"A result is available for {test.name}.",
            category="laboratory",
            target_url="/laboratory",
        )
        return report


def review_lab_report(*, report, actor):
    with transaction.atomic():
        report = (
            LabReport.objects.select_for_update()
            .select_related("test__consultation__appointment__doctor__user")
            .get(pk=report.pk)
        )
        if not _can_manage(report.test.consultation, actor):
            raise PermissionDenied(
                "Only the assigned doctor or an administrator can review results."
            )
        if report.reviewed_at is not None:
            raise ValidationError("This laboratory report has already been reviewed.")
        report.reviewed_at = timezone.now()
        report.save(update_fields=("reviewed_at",))
        record_event(actor=actor, action="lab_report.reviewed", instance=report)
    return report
