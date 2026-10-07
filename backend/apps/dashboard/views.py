from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment, QueueEntry
from apps.billing.models import Invoice
from apps.consultations.models import Consultation
from apps.laboratory.models import LabReport
from apps.patients.models import PatientProfile
from apps.prescriptions.models import Prescription

User = get_user_model()


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        appointments = Appointment.objects.all()

        if user.role == User.Role.ADMIN:
            return Response(self._admin_dashboard(today, appointments))
        if user.role == User.Role.DOCTOR:
            return Response(self._doctor_dashboard(user, today, appointments))
        if user.role == User.Role.RECEPTIONIST:
            return Response(self._reception_dashboard(today, appointments))
        return Response(self._patient_dashboard(user, today, appointments))

    def _admin_dashboard(self, today, appointments):
        start_month = today.replace(day=1)
        six_months_ago = (start_month - timedelta(days=150)).replace(day=1)
        appointments_by_month = (
            appointments.filter(starts_at__date__gte=six_months_ago)
            .annotate(month=TruncMonth("starts_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        revenue_by_month = (
            Invoice.objects.filter(
                status=Invoice.Status.PAID,
                paid_at__date__gte=six_months_ago,
            )
            .annotate(month=TruncMonth("paid_at"))
            .values("month")
            .annotate(
                total=Sum(
                    ExpressionWrapper(
                        F("items__quantity") * F("items__unit_price"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                )
            )
            .order_by("month")
        )
        completed = appointments.filter(status=Appointment.Status.COMPLETED).count()
        cancelled = appointments.filter(status=Appointment.Status.CANCELLED).count()
        revenue = sum(
            (
                invoice.total
                for invoice in Invoice.objects.filter(status=Invoice.Status.PAID)
                .prefetch_related("items")
            ),
            start=0,
        )
        return {
            "role": "admin",
            "totals": {
                "patients": PatientProfile.objects.count(),
                "doctors": User.objects.filter(role=User.Role.DOCTOR, is_active=True).count(),
                "today_appointments": appointments.filter(starts_at__date=today).count(),
                "completed_appointments": completed,
                "cancelled_appointments": cancelled,
                "revenue": str(revenue),
            },
            "appointment_trend": [
                {"month": row["month"].date().isoformat(), "count": row["total"]}
                for row in appointments_by_month
            ],
            "revenue_trend": [
                {
                    "month": row["month"].date().isoformat(),
                    "amount": f"{row['total'] or 0:.2f}",
                }
                for row in revenue_by_month
            ],
        }

    def _doctor_dashboard(self, user, today, appointments):
        own_appointments = appointments.filter(doctor__user=user)
        completed = Consultation.objects.filter(
            appointment__doctor__user=user,
            status=Consultation.Status.COMPLETED,
        ).count()
        pending = Consultation.objects.filter(
            appointment__doctor__user=user,
            status=Consultation.Status.IN_PROGRESS,
        ).count()
        follow_ups = Consultation.objects.filter(
            appointment__doctor__user=user,
            follow_up_date__gte=today,
        ).select_related("appointment__patient__user").order_by("follow_up_date")[:10]
        return {
            "role": "doctor",
            "totals": {
                "today_appointments": own_appointments.filter(starts_at__date=today).count(),
                "completed_consultations": completed,
                "pending_consultations": pending,
                "follow_ups": follow_ups.count(),
            },
            "follow_up_list": [
                {
                    "date": item.follow_up_date.isoformat(),
                    "patient": item.appointment.patient.user.get_full_name()
                    or item.appointment.patient.user.email,
                }
                for item in follow_ups
            ],
            "today_appointments": [
                {
                    "id": appointment.pk,
                    "patient": appointment.patient.user.get_full_name()
                    or appointment.patient.user.email,
                    "starts_at": appointment.starts_at.isoformat(),
                    "status": appointment.status,
                }
                for appointment in own_appointments.filter(starts_at__date=today)
                .select_related("patient__user")
            ],
        }

    def _reception_dashboard(self, today, appointments):
        return {
            "role": "receptionist",
            "totals": {
                "today_appointments": appointments.filter(starts_at__date=today).count(),
                "checked_in": appointments.filter(
                    starts_at__date=today,
                    status=Appointment.Status.CHECKED_IN,
                ).count(),
                "waiting": appointments.filter(
                    queue_entry__queue_date=today,
                    queue_entry__status=QueueEntry.Status.WAITING,
                ).count(),
                "scheduled": appointments.filter(
                    starts_at__date=today,
                    status=Appointment.Status.SCHEDULED,
                ).count(),
            },
        }

    def _patient_dashboard(self, user, today, appointments):
        own_appointments = appointments.filter(patient__user=user)
        recent_reports = LabReport.objects.filter(
            test__consultation__appointment__patient__user=user,
        ).select_related("test").order_by("-reported_at")[:5]
        recent_prescriptions = Prescription.objects.filter(
            consultation__appointment__patient__user=user,
        ).order_by("-created_at")[:5]
        return {
            "role": "patient",
            "totals": {
                "upcoming_appointments": own_appointments.filter(
                    starts_at__date__gte=today,
                    status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED),
                ).count(),
                "completed_appointments": own_appointments.filter(
                    status=Appointment.Status.COMPLETED
                ).count(),
                "recent_prescriptions": recent_prescriptions.count(),
                "recent_reports": recent_reports.count(),
            },
            "upcoming": [
                {
                    "id": appointment.pk,
                    "doctor": appointment.doctor.user.get_full_name()
                    or appointment.doctor.user.email,
                    "starts_at": appointment.starts_at.isoformat(),
                }
                for appointment in own_appointments.filter(
                    starts_at__date__gte=today,
                    status__in=(Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED),
                ).select_related("doctor__user")[:5]
            ],
            "recent_prescriptions": [
                {"id": item.pk, "created_at": item.created_at.isoformat()}
                for item in recent_prescriptions
            ],
            "recent_reports": [
                {"id": report.pk, "test": report.test.name, "reported_at": report.reported_at.isoformat()}
                for report in recent_reports
            ],
        }
