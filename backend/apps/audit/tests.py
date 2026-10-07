from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AuditLog

User = get_user_model()


class AuditLogApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@example.com",
            "Audit-Admin-Passphrase-910!",
            role=User.Role.ADMIN,
        )
        self.patient = User.objects.create_user(
            "patient@example.com",
            "Audit-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        AuditLog.objects.create(
            actor=self.admin,
            action="appointment.created",
            object_type="appointments.appointment",
            object_id="1",
        )

    def test_only_administrators_can_view_audit_logs(self):
        self.client.force_authenticate(self.patient)
        denied = self.client.get(reverse("audit-log-list"))
        self.client.force_authenticate(self.admin)
        allowed = self.client.get(reverse("audit-log-list"))

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(allowed.data), 1)
