from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.clinics.models import Department, DoctorProfile
from apps.consultations.models import Consultation
from apps.patients.models import PatientProfile

from .models import LabReport, LabTest

User = get_user_model()


class LaboratoryApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Laboratory-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        patient = PatientProfile.objects.create(user=self.patient_user)
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Laboratory-Doctor-Passphrase-912!",
            role=User.Role.DOCTOR,
        )
        doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=Department.objects.create(name="Laboratory Medicine"),
            license_number="LAB-911",
            specialization="General Practice",
        )
        starts = timezone.now()
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=30),
            status=Appointment.Status.IN_CONSULTATION,
        )
        self.consultation = Consultation.objects.create(appointment=appointment)

    def test_doctor_requests_test_records_result_and_patient_reads_report(self):
        self.client.force_authenticate(self.doctor_user)
        request = self.client.post(
            reverse("lab-test-list"),
            {
                "consultation": self.consultation.pk,
                "name": "Complete blood count",
                "clinical_question": "Check for anemia",
            },
            format="json",
        )
        self.assertEqual(request.status_code, status.HTTP_201_CREATED)
        self.assertEqual(request.data["appointment_id"], self.consultation.appointment_id)
        test_id = request.data["id"]
        result = self.client.post(
            reverse("lab-test-reports", args=(test_id,)),
            {"result_text": "Results within expected range."},
            format="json",
        )
        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        self.assertEqual(result.data["status"], LabTest.Status.COMPLETED)
        self.assertEqual(LabReport.objects.count(), 1)
        self.assertEqual(len(result.data["reports"]), 1)

        report_id = result.data["reports"][0]["id"]
        review = self.client.post(
            reverse("lab-test-review-report", args=(test_id,)),
            {"report": report_id},
            format="json",
        )
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(review.data["reports"][0]["reviewed_at"])

        self.client.force_authenticate(self.patient_user)
        response = self.client.get(reverse("lab-test-detail", args=(test_id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reports"][0]["result_text"], "Results within expected range.")
