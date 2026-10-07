from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.clinics.models import Department, DoctorProfile
from apps.patients.models import PatientProfile

from .models import Invoice

User = get_user_model()


class BillingApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Billing-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        patient = PatientProfile.objects.create(user=self.patient_user)
        self.receptionist = User.objects.create_user(
            "reception@example.com",
            "Billing-Reception-Passphrase-912!",
            role=User.Role.RECEPTIONIST,
        )
        self.billing_user = User.objects.create_user(
            "billing@example.com",
            "Billing-Counter-Passphrase-915!",
            role=User.Role.BILLING,
        )
        doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Billing-Doctor-Passphrase-913!",
            role=User.Role.DOCTOR,
        )
        doctor = DoctorProfile.objects.create(
            user=doctor_user,
            department=Department.objects.create(name="Billing Medicine"),
            license_number="BILL-911",
            specialization="General Practice",
        )
        starts = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=30),
            status=Appointment.Status.COMPLETED,
        )

    def test_staff_create_issue_and_mark_invoice_paid(self):
        self.client.force_authenticate(self.receptionist)
        create = self.client.post(
            reverse("invoice-list"),
            {
                "appointment": self.appointment.pk,
                "currency": "USD",
                "discount_amount": "1.50",
                "items": [
                    {"description": "Consultation", "quantity": 1, "unit_price": "75.00"},
                    {"description": "Supply", "quantity": 2, "unit_price": "3.25"},
                ],
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create.data["subtotal"], "81.50")
        self.assertEqual(create.data["discount_amount"], "1.50")
        self.assertEqual(create.data["total"], "80.00")
        invoice_id = create.data["id"]

        issued = self.client.post(
            reverse("invoice-status", args=(invoice_id,)),
            {"status": Invoice.Status.ISSUED},
            format="json",
        )
        missing_payment_method = self.client.post(
            reverse("invoice-status", args=(invoice_id,)),
            {"status": Invoice.Status.PAID},
            format="json",
        )
        paid = self.client.post(
            reverse("invoice-status", args=(invoice_id,)),
            {
                "status": Invoice.Status.PAID,
                "payment_method": Invoice.PaymentMethod.UPI,
                "transaction_reference": "TXN-TEST-123",
            },
            format="json",
        )

        self.assertEqual(issued.status_code, status.HTTP_200_OK)
        self.assertEqual(missing_payment_method.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        self.assertEqual(paid.data["status"], Invoice.Status.PAID)
        self.assertEqual(paid.data["payment_method"], Invoice.PaymentMethod.UPI)
        self.assertEqual(paid.data["transaction_reference"], "TXN-TEST-123")
        self.assertEqual(paid.data["invoice_number"][:4], "INV-")
        self.assertEqual(paid.data["patient_number"], self.appointment.patient.patient_number)
        self.assertEqual(paid.data["department_name"], "Billing Medicine")

    def test_invoice_rejects_discount_above_subtotal(self):
        self.client.force_authenticate(self.receptionist)
        response = self.client.post(
            reverse("invoice-list"),
            {
                "appointment": self.appointment.pk,
                "discount_amount": "10.00",
                "items": [{"description": "Consultation", "quantity": 1, "unit_price": "5.00"}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("discount_amount", response.data)

    def test_patient_can_only_read_own_invoice_and_cannot_create_one(self):
        invoice = Invoice.objects.create(
            appointment=self.appointment,
            created_by=self.receptionist,
        )
        self.client.force_authenticate(self.patient_user)
        read = self.client.get(reverse("invoice-detail", args=(invoice.pk,)))
        create = self.client.post(
            reverse("invoice-list"),
            {"appointment": self.appointment.pk, "items": [{"description": "x", "unit_price": "1.00"}]},
            format="json",
        )

        self.assertEqual(read.status_code, status.HTTP_200_OK)
        self.assertEqual(create.status_code, status.HTTP_403_FORBIDDEN)

    def test_billing_role_can_create_and_record_counter_payment(self):
        self.client.force_authenticate(self.billing_user)
        created = self.client.post(
            reverse("invoice-list"),
            {
                "appointment": self.appointment.pk,
                "items": [
                    {"description": "Consultation", "quantity": 1, "unit_price": "500.00"}
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        invoice_id = created.data["id"]
        self.client.post(
            reverse("invoice-status", args=(invoice_id,)),
            {"status": Invoice.Status.ISSUED},
            format="json",
        )
        paid = self.client.post(
            reverse("invoice-status", args=(invoice_id,)),
            {
                "status": Invoice.Status.PAID,
                "payment_method": Invoice.PaymentMethod.CASH,
            },
            format="json",
        )

        self.assertEqual(paid.status_code, status.HTTP_200_OK)
        self.assertEqual(paid.data["currency"], "INR")
        self.assertEqual(paid.data["payment_method"], Invoice.PaymentMethod.CASH)

    def test_billing_user_can_only_query_minimal_unbilled_appointment_data(self):
        endpoint = reverse("invoice-unbilled-appointments")
        self.client.force_authenticate(self.billing_user)

        available = self.client.get(endpoint)

        self.assertEqual(available.status_code, status.HTTP_200_OK)
        self.assertEqual(len(available.data), 1)
        self.assertEqual(available.data[0]["patient_number"], self.appointment.patient.patient_number)
        self.assertNotIn("reason", available.data[0])

        self.client.force_authenticate(self.patient_user)
        forbidden = self.client.get(endpoint)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
