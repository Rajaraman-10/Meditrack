from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.billing.models import Invoice, InvoiceItem
from apps.clinics.models import Department, DoctorProfile
from apps.consultations.models import Consultation
from apps.patients.models import PatientProfile

from .models import Medicine, Prescription

User = get_user_model()


class PrescriptionApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Prescription-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Prescription-Doctor-Passphrase-912!",
            role=User.Role.DOCTOR,
        )
        self.billing_user = User.objects.create_user(
            "billing@example.com",
            "Prescription-Billing-Passphrase-914!",
            role=User.Role.BILLING,
        )
        department = Department.objects.create(name="Prescription Medicine")
        doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=department,
            license_number="RX-911",
            specialization="General Practice",
        )
        starts = timezone.now()
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=doctor,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=30),
            status=Appointment.Status.IN_CONSULTATION,
        )
        self.consultation = Consultation.objects.create(appointment=appointment)

    def test_doctor_can_create_prescription_and_patient_can_read_own(self):
        self.consultation.status = Consultation.Status.COMPLETED
        self.consultation.save(update_fields=("status",))
        medicine, _ = Medicine.objects.get_or_create(
            name="Paracetamol",
            strength="500 mg",
            dosage_form="tablet",
            defaults={"generic_name": "Paracetamol"},
        )
        self.client.force_authenticate(self.doctor_user)
        create = self.client.post(
            reverse("prescription-list"),
            {
                "consultation": self.consultation.pk,
                "instructions": "Take with food.",
                "items": [{
                    "medicine": medicine.pk,
                    "dosage": "1 tablet",
                    "route": "oral",
                    "frequency": "twice daily",
                    "duration": "5 days",
                    "instructions": "",
                    "food_timing": "after_food",
                }],
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(create.data["items"]), 1)
        self.assertEqual(create.data["items"][0]["medication_name"], "Paracetamol")
        self.assertEqual(create.data["items"][0]["strength"], "500 mg")
        self.assertEqual(create.data["items"][0]["food_timing"], "after_food")
        self.assertEqual(create.data["patient_number"], self.patient.patient_number)
        self.assertEqual(create.data["department_name"], "Prescription Medicine")
        self.assertEqual(create.data["status"], Prescription.Status.PAYMENT_PENDING)

        self.client.force_authenticate(self.patient_user)
        patient_list = self.client.get(reverse("prescription-list"))
        self.assertEqual(patient_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(patient_list.data), 0)
        hidden_detail = self.client.get(
            reverse("prescription-detail", args=(create.data["id"],))
        )
        self.assertEqual(hidden_detail.status_code, status.HTTP_404_NOT_FOUND)

        invoice = Invoice.objects.create(
            appointment=self.consultation.appointment,
            created_by=self.billing_user,
            currency="INR",
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            description="Consultation",
            quantity=1,
            unit_price="650.00",
        )
        invoice.status = Invoice.Status.PAID
        invoice.payment_method = Invoice.PaymentMethod.UPI
        invoice.paid_at = timezone.now()
        invoice.save(
            update_fields=("status", "payment_method", "paid_at", "updated_at"),
        )

        self.client.force_authenticate(self.billing_user)
        released = self.client.post(
            reverse("prescription-release", args=(create.data["id"],)),
        )
        self.assertEqual(released.status_code, status.HTTP_200_OK)
        self.assertEqual(released.data["status"], Prescription.Status.RELEASED)

        self.client.force_authenticate(self.patient_user)
        patient_list = self.client.get(reverse("prescription-list"))
        self.assertEqual(patient_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(patient_list.data), 1)
        self.assertEqual(patient_list.data[0]["id"], create.data["id"])

    def test_medicine_search_returns_catalog_matches(self):
        Medicine.objects.get_or_create(
            name="Paracetamol",
            strength="500 mg",
            dosage_form="tablet",
            defaults={"generic_name": "Paracetamol"},
        )
        Medicine.objects.get_or_create(
            name="Amoxicillin",
            strength="500 mg",
            dosage_form="capsule",
            defaults={"generic_name": "Amoxicillin"},
        )
        self.client.force_authenticate(self.doctor_user)

        response = self.client.get(reverse("medicine-list"), {"search": "para"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertTrue(all(item["generic_name"] == "Paracetamol" for item in response.data))

    def test_assigned_doctor_can_issue_prescription_after_consultation_completion(self):
        self.consultation.status = Consultation.Status.COMPLETED
        self.consultation.save(update_fields=("status",))
        self.consultation.appointment.status = Appointment.Status.COMPLETED
        self.consultation.appointment.save(update_fields=("status",))
        self.client.force_authenticate(self.doctor_user)

        response = self.client.post(
            reverse("prescription-list"),
            {
                "consultation": self.consultation.pk,
                "instructions": "Prescription recorded after consultation completion.",
                "items": [{
                    "medication_name": "Follow-up medicine",
                    "strength": "10 mg",
                    "dosage": "1 tablet",
                    "route": "oral",
                    "frequency": "once daily",
                    "duration": "5 days",
                    "food_timing": "after_food",
                }],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(
            response.data["instructions"],
            "Prescription recorded after consultation completion.",
        )
        self.assertEqual(response.data["status"], Prescription.Status.PAYMENT_PENDING)

    def test_doctor_cannot_issue_prescription_before_consultation_is_completed(self):
        self.client.force_authenticate(self.doctor_user)

        response = self.client.post(
            reverse("prescription-list"),
            {
                "consultation": self.consultation.pk,
                "items": [{
                    "medication_name": "Follow-up medicine",
                    "strength": "10 mg",
                    "dosage": "1 tablet",
                    "route": "oral",
                    "frequency": "once daily",
                    "duration": "5 days",
                    "food_timing": "after_food",
                }],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Prescription.objects.count(), 0)

    def test_billing_cannot_release_prescription_until_invoice_is_paid(self):
        self.consultation.status = Consultation.Status.COMPLETED
        self.consultation.save(update_fields=("status",))
        self.client.force_authenticate(self.doctor_user)
        response = self.client.post(
            reverse("prescription-list"),
            {
                "consultation": self.consultation.pk,
                "items": [{
                    "medication_name": "Follow-up medicine",
                    "strength": "10 mg",
                    "dosage": "1 tablet",
                    "route": "oral",
                    "frequency": "once daily",
                    "duration": "5 days",
                    "food_timing": "after_food",
                }],
            },
            format="json",
        )
        prescription_id = response.data["id"]
        self.client.force_authenticate(self.doctor_user)
        doctor_release = self.client.post(
            reverse("prescription-release", args=(prescription_id,)),
        )
        self.assertEqual(doctor_release.status_code, status.HTTP_403_FORBIDDEN)

        Invoice.objects.create(
            appointment=self.consultation.appointment,
            created_by=self.billing_user,
        )
        self.client.force_authenticate(self.billing_user)
        queue = self.client.get(reverse("prescription-release-queue"))
        release = self.client.post(
            reverse("prescription-release", args=(prescription_id,)),
        )

        self.assertEqual(queue.status_code, status.HTTP_200_OK)
        self.assertEqual(queue.data[0]["invoice_status"], Invoice.Status.DRAFT)
        self.assertFalse(queue.data[0]["can_release"])
        self.assertEqual(release.status_code, status.HTTP_400_BAD_REQUEST)

    def test_medicine_csv_import_is_repeatable_and_keeps_route(self):
        csv_content = (
            "medicine_id,medicine_name,generic_name,strength,dosage_form,route,manufacturer,is_active\n"
            "1001,Clinic Example 10 mg Tablet,Example,10 mg,Tablet,Oral,Generic,True\n"
        )
        with TemporaryDirectory() as directory:
            csv_path = Path(directory) / "medicines.csv"
            csv_path.write_text(csv_content, encoding="utf-8")

            call_command("import_medicines", str(csv_path), stdout=StringIO())
            call_command("import_medicines", str(csv_path), stdout=StringIO())

        medicine = Medicine.objects.get(
            name="Clinic Example 10 mg Tablet",
            strength="10 mg",
            dosage_form="Tablet",
        )
        self.assertEqual(medicine.route, "Oral")
        self.assertEqual(medicine.source_id, 1001)
        self.assertEqual(
            Medicine.objects.filter(name="Clinic Example 10 mg Tablet").count(),
            1,
        )
        self.assertFalse(
            Medicine.objects.get(name="Paracetamol", strength="500 mg").is_active
        )

    def test_doctor_can_record_a_medicine_not_yet_in_catalog(self):
        self.consultation.status = Consultation.Status.COMPLETED
        self.consultation.save(update_fields=("status",))
        self.client.force_authenticate(self.doctor_user)

        response = self.client.post(
            reverse("prescription-list"),
            {
                "consultation": self.consultation.pk,
                "items": [{
                    "medication_name": "Clinic-specific medicine",
                    "strength": "10 mg",
                    "dosage": "1 tablet",
                    "route": "oral",
                    "frequency": "once daily",
                    "duration": "3 days",
                    "food_timing": "any",
                }],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["items"][0]["medication_name"],
            "Clinic-specific medicine",
        )
        self.assertEqual(response.data["items"][0]["strength"], "10 mg")

    def test_patient_cannot_create_prescription(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            reverse("prescription-list"),
            {"consultation": self.consultation.pk, "items": []},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Prescription.objects.count(), 0)
