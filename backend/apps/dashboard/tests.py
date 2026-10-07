from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment, QueueEntry
from apps.billing.models import Invoice, InvoiceItem
from apps.clinics.models import Department, DoctorProfile
from apps.patients.models import PatientProfile

User = get_user_model()


class DashboardApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@example.com",
            "Dashboard-Admin-Passphrase-910!",
            role=User.Role.ADMIN,
        )
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Dashboard-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.other_patient_user = User.objects.create_user(
            "other@example.com",
            "Dashboard-Other-Passphrase-912!",
            role=User.Role.PATIENT,
        )
        self.other_patient = PatientProfile.objects.create(user=self.other_patient_user)
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Dashboard-Doctor-Passphrase-913!",
            role=User.Role.DOCTOR,
        )
        doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=Department.objects.create(name="Dashboard Medicine"),
            license_number="DASH-910",
            specialization="General Practice",
        )
        start = timezone.now() + timedelta(days=1)
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=doctor,
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
        )
        self.other_appointment = Appointment.objects.create(
            patient=self.other_patient,
            doctor=doctor,
            starts_at=start + timedelta(minutes=30),
            ends_at=start + timedelta(minutes=60),
        )

    def test_patient_dashboard_only_includes_own_appointments(self):
        self.client.force_authenticate(self.patient_user)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "patient")
        self.assertEqual(response.data["totals"]["upcoming_appointments"], 1)
        self.assertEqual([item["id"] for item in response.data["upcoming"]], [self.appointment.pk])

    def test_admin_dashboard_returns_trends_and_paid_revenue(self):
        invoice = Invoice.objects.create(
            appointment=self.appointment,
            created_by=self.admin,
            status=Invoice.Status.PAID,
            paid_at=timezone.now(),
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Consultation",
            quantity=2,
            unit_price=Decimal("12.50"),
        )
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], "admin")
        self.assertEqual(response.data["totals"]["revenue"], "25.00")
        self.assertTrue(response.data["appointment_trend"])
        self.assertEqual(response.data["revenue_trend"][0]["amount"], "25.00")

    def test_reception_dashboard_counts_queue_entries_separately(self):
        QueueEntry.objects.create(
            appointment=self.appointment,
            doctor=self.appointment.doctor,
            queue_date=timezone.localdate(),
            position=1,
            status=QueueEntry.Status.LEFT,
        )
        self.appointment.starts_at = timezone.now()
        self.appointment.ends_at = self.appointment.starts_at + timedelta(minutes=30)
        self.appointment.status = Appointment.Status.CHECKED_IN
        self.appointment.save(update_fields=("starts_at", "ends_at", "status"))
        receptionist = User.objects.create_user(
            "reception@example.com",
            "Dashboard-Reception-Passphrase-914!",
            role=User.Role.RECEPTIONIST,
        )
        self.client.force_authenticate(receptionist)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["totals"]["waiting"], 0)
