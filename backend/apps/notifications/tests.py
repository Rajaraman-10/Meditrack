from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification

User = get_user_model()


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "patient@example.com",
            "Notification-Patient-Passphrase-911!",
            role=User.Role.PATIENT,
        )
        self.other_user = User.objects.create_user(
            "other@example.com",
            "Notification-Other-Passphrase-912!",
            role=User.Role.PATIENT,
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Test message",
            message="A private message",
        )
        self.other_notification = Notification.objects.create(
            recipient=self.other_user,
            title="Private",
            message="Not yours",
        )

    def test_users_only_read_and_mark_own_notifications(self):
        self.client.force_authenticate(self.user)
        listing = self.client.get(reverse("notification-list"))
        forbidden = self.client.post(
            reverse("notification-read", args=(self.other_notification.pk,))
        )
        read = self.client.post(
            reverse("notification-read", args=(self.notification.pk,))
        )

        self.assertEqual(len(listing.data), 1)
        self.assertEqual(forbidden.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(read.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertIsNotNone(self.notification.read_at)
