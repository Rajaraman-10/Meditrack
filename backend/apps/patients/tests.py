from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.clinics.models import Department, DoctorProfile

from .models import PatientProfile

User = get_user_model()


class PatientApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Patient-Testing-Passphrase-718!",
            role=User.Role.PATIENT,
        )
        self.patient = PatientProfile.objects.create(
            user=self.patient_user,
            phone="555-0101",
        )
        self.other_patient_user = User.objects.create_user(
            "other.patient@example.com",
            "Patient-Testing-Passphrase-719!",
            role=User.Role.PATIENT,
        )
        self.other_patient = PatientProfile.objects.create(
            user=self.other_patient_user,
        )
        self.receptionist = User.objects.create_user(
            "reception@example.com",
            "Reception-Testing-Passphrase-720!",
            role=User.Role.RECEPTIONIST,
        )
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Doctor-Testing-Passphrase-723!",
            role=User.Role.DOCTOR,
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=Department.objects.create(name="General Medicine"),
            license_number="DOC-TEST-001",
            specialization="General Medicine",
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at="2026-10-15T10:30:00Z",
            ends_at="2026-10-15T11:00:00Z",
        )

    def test_patient_number_is_generated_unique_and_read_only(self):
        self.assertRegex(self.patient.patient_number, r"^MED-\d{6,}$")
        self.assertNotEqual(self.patient.patient_number, self.other_patient.patient_number)

        self.client.force_authenticate(self.patient_user)
        response = self.client.patch(
            reverse("patients:patient-detail", args=(self.patient.pk,)),
            {"patient_number": "MED-999999"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertNotEqual(self.patient.patient_number, "MED-999999")

    def test_doctor_can_search_and_view_patient_with_their_appointment(self):
        self.client.force_authenticate(self.doctor_user)

        search_response = self.client.get(
            reverse("patients:doctor-patient-search"),
            {"patient_number": self.patient.patient_number.lower()},
        )
        record_response = self.client.get(
            reverse("patients:doctor-patient-record", args=(self.patient.pk,))
        )

        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(search_response.data["patient_number"], self.patient.patient_number)
        self.assertEqual(record_response.status_code, status.HTTP_200_OK)
        self.assertEqual(record_response.data["patient"]["id"], self.patient.pk)
        self.assertEqual(len(record_response.data["appointments"]), 1)
        self.assertEqual(
            AuditLog.objects.filter(
                actor=self.doctor_user,
                action="patient.search",
                object_id=str(self.patient.pk),
            ).count(),
            1,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.doctor_user,
                action="patient.record_viewed",
                object_id=str(self.patient.pk),
            ).exists()
        )

    def test_doctor_cannot_discover_patient_without_an_appointment(self):
        self.client.force_authenticate(self.doctor_user)

        response = self.client.get(
            reverse("patients:doctor-patient-search"),
            {"patient_number": self.other_patient.patient_number},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No accessible patient was found for that patient number.")
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.doctor_user,
                action="patient.search",
                object_id=str(self.other_patient.pk),
                metadata__result="not_authorized",
            ).exists()
        )

    def test_non_doctor_cannot_use_doctor_patient_search(self):
        self.client.force_authenticate(self.receptionist)

        response = self.client.get(
            reverse("patients:doctor-patient-search"),
            {"patient_number": self.patient.patient_number},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_only_list_and_update_own_profile(self):
        self.client.force_authenticate(self.patient_user)

        list_response = self.client.get(reverse("patients:patient-list"))
        own_detail = self.client.get(
            reverse("patients:patient-detail", args=(self.patient.pk,))
        )
        other_detail = self.client.get(
            reverse("patients:patient-detail", args=(self.other_patient.pk,))
        )
        update_response = self.client.patch(
            reverse("patients:patient-detail", args=(self.patient.pk,)),
            {"phone": "555-0123"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(own_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(other_detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.phone, "555-0123")

    def test_receptionist_can_list_and_register_patient(self):
        self.client.force_authenticate(self.receptionist)

        list_response = self.client.get(reverse("patients:patient-list"))
        create_response = self.client.post(
            reverse("patients:patient-list"),
            {
                "email": "walkin@example.com",
                "password": "Walk-In-Patient-Passphrase-721!",
                "first_name": "Walk",
                "last_name": "In",
                "phone": "555-0102",
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 2)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertRegex(create_response.data["patient_number"], r"^MED-\d{6,}$")
        self.assertTrue(
            PatientProfile.objects.filter(user__email="walkin@example.com").exists()
        )

    def test_patient_cannot_register_another_patient_or_change_login_identity(self):
        self.client.force_authenticate(self.patient_user)
        create_response = self.client.post(
            reverse("patients:patient-list"),
            {
                "email": "intruder@example.com",
                "password": "Patient-Testing-Passphrase-722!",
                "first_name": "Intruder",
                "last_name": "Patient",
            },
            format="json",
        )
        update_response = self.client.patch(
            reverse("patients:patient-detail", args=(self.patient.pk,)),
            {"email": "changed@example.com"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.patient_user.refresh_from_db()
        self.assertEqual(self.patient_user.email, "patient@example.com")
