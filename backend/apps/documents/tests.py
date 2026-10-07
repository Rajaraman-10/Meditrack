from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.clinics.models import Department, DoctorProfile
from apps.patients.models import PatientProfile

from .models import MedicalDocument

User = get_user_model()


class MedicalDocumentApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Document-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.other_patient_user = User.objects.create_user(
            "other@example.com",
            "Document-Other-Passphrase-912!",
            role=User.Role.PATIENT,
        )
        self.other_patient = PatientProfile.objects.create(user=self.other_patient_user)
        self.receptionist = User.objects.create_user(
            "reception@example.com",
            "Document-Reception-Passphrase-913!",
            role=User.Role.RECEPTIONIST,
        )
        doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Document-Doctor-Passphrase-914!",
            role=User.Role.DOCTOR,
        )
        doctor = DoctorProfile.objects.create(
            user=doctor_user,
            department=Department.objects.create(name="Document Medicine"),
            license_number="DOC-911",
            specialization="General Practice",
        )
        starts = timezone.now()
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=doctor,
            starts_at=starts,
            ends_at=starts + timedelta(minutes=30),
        )

        self.temporary_media = TemporaryDirectory()
        self.addCleanup(self.temporary_media.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=self.temporary_media.name))

    def test_patient_uploads_and_downloads_private_document(self):
        self.client.force_authenticate(self.patient_user)
        upload = self.client.post(
            reverse("medical-document-list"),
            {
                "title": "Referral letter",
                "category": "referral",
                "file": SimpleUploadedFile("referral.pdf", b"%PDF-1.4 demo", content_type="application/pdf"),
            },
            format="multipart",
        )

        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("file", upload.data)
        download = self.client.get(
            reverse("medical-document-download", args=(upload.data["id"],))
        )
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        download.close()

        self.client.force_authenticate(self.other_patient_user)
        hidden = self.client.get(
            reverse("medical-document-download", args=(upload.data["id"],))
        )
        self.assertEqual(hidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_document_extension_and_size_validation(self):
        self.client.force_authenticate(self.patient_user)
        invalid = self.client.post(
            reverse("medical-document-list"),
            {
                "title": "Executable",
                "category": "other",
                "file": SimpleUploadedFile("payload.exe", b"not safe"),
            },
            format="multipart",
        )
        oversized = self.client.post(
            reverse("medical-document-list"),
            {
                "title": "Too large",
                "category": "other",
                "file": SimpleUploadedFile("large.pdf", b"x" * (10 * 1024 * 1024 + 1)),
            },
            format="multipart",
        )

        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(oversized.status_code, status.HTTP_400_BAD_REQUEST)
