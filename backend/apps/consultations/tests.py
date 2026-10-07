from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment, QueueEntry
from apps.clinics.models import Department, DoctorProfile
from apps.patients.models import PatientProfile

from .models import Consultation

User = get_user_model()


class ConsultationApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Consultation-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Consultation-Doctor-Passphrase-912!",
            role=User.Role.DOCTOR,
        )
        department = Department.objects.create(name="Consultation Medicine")
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=department,
            license_number="CONSULT-911",
            specialization="General Practice",
        )
        self.receptionist = User.objects.create_user(
            "reception@example.com",
            "Consultation-Reception-Passphrase-913!",
            role=User.Role.RECEPTIONIST,
        )
        now = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at=now,
            ends_at=now + timedelta(minutes=30),
            status=Appointment.Status.CHECKED_IN,
        )
        self.queue_entry = QueueEntry.objects.create(
            appointment=self.appointment,
            doctor=self.doctor,
            queue_date=timezone.localdate(),
            position=1,
        )

    def test_assigned_doctor_starts_updates_and_completes_consultation(self):
        self.client.force_authenticate(self.doctor_user)
        start = self.client.post(
            reverse("consultation-list"),
            {"appointment": self.appointment.pk},
            format="json",
        )
        self.assertEqual(start.status_code, status.HTTP_201_CREATED)
        consultation_id = start.data["id"]

        update = self.client.patch(
            reverse("consultation-detail", args=(consultation_id,)),
            {
                "diagnosis": "Acute viral upper respiratory infection",
                "clinical_notes": "Hydration and rest advised.",
                "follow_up_date": (timezone.localdate() + timedelta(days=7)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)

        complete = self.client.post(
            reverse("consultation-complete", args=(consultation_id,)),
            format="json",
        )
        self.assertEqual(complete.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.queue_entry.refresh_from_db()
        self.assertEqual(complete.data["status"], Consultation.Status.COMPLETED)
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)
        self.assertEqual(self.queue_entry.status, QueueEntry.Status.COMPLETED)

    def test_other_doctor_cannot_access_or_start_consultation(self):
        other_user = User.objects.create_user(
            "other.doctor@example.com",
            "Other-Consultation-Doctor-914!",
            role=User.Role.DOCTOR,
        )
        self.client.force_authenticate(other_user)
        response = self.client.post(
            reverse("consultation-list"),
            {"appointment": self.appointment.pk},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Consultation.objects.count(), 0)

    def test_receptionist_cannot_read_clinical_consultation(self):
        consultation = Consultation.objects.create(appointment=self.appointment)
        self.client.force_authenticate(self.receptionist)

        response = self.client.get(
            reverse("consultation-detail", args=(consultation.pk,))
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

