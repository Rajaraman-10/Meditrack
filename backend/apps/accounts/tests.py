from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.patients.models import PatientProfile


class UserManagerTests(TestCase):
    def test_create_user_normalizes_email_and_hashes_password(self):
        user = get_user_model().objects.create_user(
            "  Alex.Example@Example.COM ",
            "safe-test-password",
        )

        self.assertEqual(user.email, "alex.example@example.com")
        self.assertTrue(user.check_password("safe-test-password"))
        self.assertNotEqual(user.password, "safe-test-password")
        self.assertEqual(user.role, get_user_model().Role.PATIENT)

    def test_create_superuser_uses_admin_role_and_staff_flags(self):
        user = get_user_model().objects.create_superuser(
            "admin@example.com",
            "safe-test-password",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, get_user_model().Role.ADMIN)

    def test_create_user_requires_email(self):
        with self.assertRaisesMessage(ValueError, "An email address is required."):
            get_user_model().objects.create_user("", "safe-test-password")

    def test_superuser_cannot_have_non_admin_role(self):
        with self.assertRaisesMessage(ValueError, "A superuser must have the admin role."):
            get_user_model().objects.create_superuser(
                "doctor@example.com",
                "safe-test-password",
                role=get_user_model().Role.DOCTOR,
            )


class AuthenticationApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            "patient@example.com",
            "Valid-Secure-Passphrase-482!",
            first_name="Alex",
        )

    def test_registration_creates_account_that_can_sign_in_immediately(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "new.patient@example.com",
                "password": "Another-Secure-Passphrase-739!",
                "first_name": "Sam",
                "role": "admin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "patient")
        self.assertRegex(response.data["patient_number"], r"^MED-\d{6,}$")
        self.assertNotIn("password", response.data)
        registered_user = get_user_model().objects.get(email="new.patient@example.com")
        self.assertEqual(registered_user.role, get_user_model().Role.PATIENT)
        self.assertTrue(
            PatientProfile.objects.filter(
                user__email="new.patient@example.com"
            ).exists()
        )
        profile = PatientProfile.objects.get(user__email="new.patient@example.com")
        self.assertEqual(response.data["patient_number"], profile.patient_number)

        login_response = self.client.post(
            reverse("accounts:login"),
            {
                "email": "new.patient@example.com",
                "password": "Another-Secure-Passphrase-739!",
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh", login_response.data)

    def test_registration_rejects_duplicate_email_and_weak_password(self):
        duplicate = self.client.post(
            reverse("accounts:register"),
            {"email": self.user.email.upper(), "password": "Another-Secure-Passphrase-739!"},
            format="json",
        )
        weak_password = self.client.post(
            reverse("accounts:register"),
            {"email": "weak@example.com", "password": "password"},
            format="json",
        )

        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(weak_password.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_returns_tokens_and_current_user_requires_bearer_token(self):
        login_response = self.client.post(
            reverse("accounts:login"),
            {"email": self.user.email, "password": "Valid-Secure-Passphrase-482!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh", login_response.data)

        anonymous_response = self.client.get(reverse("accounts:current-user"))
        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        profile_response = self.client.get(reverse("accounts:current-user"))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data["email"], self.user.email)
        self.assertNotIn("password", profile_response.data)

    def test_refresh_token_can_be_refreshed_and_revoked_on_logout(self):
        refresh = RefreshToken.for_user(self.user)
        refresh_value = str(refresh)

        refresh_response = self.client.post(
            reverse("accounts:refresh"),
            {"refresh": refresh_value},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

        self.client.force_authenticate(self.user)
        logout_response = self.client.post(
            reverse("accounts:logout"),
            {"refresh": refresh_value},
            format="json",
        )
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        rejected_refresh = self.client.post(
            reverse("accounts:refresh"),
            {"refresh": refresh_value},
            format="json",
        )
        self.assertEqual(rejected_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_can_login_refresh_and_access_api(self):
        pending_user = get_user_model().objects.create_user(
            "pending@example.com",
            "Pending-Patient-Passphrase-712!",
        )
        refresh = RefreshToken.for_user(pending_user)
        login = self.client.post(
            reverse("accounts:login"),
            {
                "email": pending_user.email,
                "password": "Pending-Patient-Passphrase-712!",
            },
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        profile = self.client.get(reverse("accounts:current-user"))
        refreshed = self.client.post(
            reverse("accounts:refresh"),
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)

    def test_email_verification_endpoints_are_removed(self):
        verify = self.client.post("/api/auth/verify-email/", {}, format="json")
        resend = self.client.post("/api/auth/resend-verification/", {}, format="json")

        self.assertEqual(verify.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resend.status_code, status.HTTP_404_NOT_FOUND)

    def test_logout_cannot_revoke_another_users_refresh_token(self):
        other_user = get_user_model().objects.create_user(
            "other@example.com",
            "Other-Secure-Passphrase-719!",
        )
        refresh = RefreshToken.for_user(other_user)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("accounts:logout"),
            {"refresh": str(refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_admin_can_provision_receptionist_accounts(self):
        admin = get_user_model().objects.create_user(
            "clinic.admin@example.com",
            "Clinic-Admin-Passphrase-839!",
            role=get_user_model().Role.ADMIN,
        )
        self.client.force_authenticate(admin)
        created = self.client.post(
            reverse("accounts:staff-users"),
            {
                "email": "desk@example.com",
                "password": "Reception-Desk-Passphrase-840!",
                "first_name": "Front",
                "last_name": "Desk",
                "role": "receptionist",
            },
            format="json",
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["role"], "receptionist")
        self.assertNotIn("password", created.data)

        self.client.force_authenticate(self.user)
        forbidden = self.client.post(
            reverse("accounts:staff-users"),
            {
                "email": "another.desk@example.com",
                "password": "Reception-Desk-Passphrase-841!",
                "first_name": "Another",
                "last_name": "Desk",
                "role": "receptionist",
            },
            format="json",
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_provision_manage_and_reset_billing_accounts(self):
        admin = get_user_model().objects.create_user(
            "staff.admin@example.com",
            "Staff-Admin-Secure-Passphrase-942!",
            role=get_user_model().Role.ADMIN,
        )
        self.client.force_authenticate(admin)
        created = self.client.post(
            reverse("accounts:staff-users"),
            {
                "email": "billing.desk@example.com",
                "password": "Billing-Desk-Secure-Passphrase-943!",
                "first_name": "Billing",
                "last_name": "Desk",
                "role": "billing",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        staff_id = created.data["id"]

        listed = self.client.get(reverse("accounts:staff-users"))
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertTrue(any(row["id"] == staff_id for row in listed.data))

        disabled = self.client.patch(
            reverse("accounts:staff-user-detail", args=(staff_id,)),
            {"is_active": False, "role": "receptionist"},
            format="json",
        )
        self.assertEqual(disabled.status_code, status.HTTP_200_OK)
        self.assertEqual(disabled.data["role"], "receptionist")
        self.assertFalse(disabled.data["is_active"])

        reset = self.client.post(
            reverse("accounts:staff-password-reset", args=(staff_id,)),
            {"password": "Billing-Desk-Reset-Passphrase-944!"},
            format="json",
        )
        self.assertEqual(reset.status_code, status.HTTP_200_OK)
        self.assertTrue(
            get_user_model().objects.get(pk=staff_id).check_password(
                "Billing-Desk-Reset-Passphrase-944!"
            )
        )
        self.client.patch(
            reverse("accounts:staff-user-detail", args=(staff_id,)),
            {"is_active": True},
            format="json",
        )
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )
        from rest_framework_simplejwt.tokens import RefreshToken

        staff_user = get_user_model().objects.get(pk=staff_id)
        refresh = RefreshToken.for_user(staff_user)
        reset_again = self.client.post(
            reverse("accounts:staff-password-reset", args=(staff_id,)),
            {"password": "Billing-Desk-Reset-Passphrase-947!"},
            format="json",
        )
        outstanding = OutstandingToken.objects.get(jti=refresh["jti"])
        self.assertEqual(reset_again.status_code, status.HTTP_200_OK)
        self.assertTrue(BlacklistedToken.objects.filter(token=outstanding).exists())

    def test_staff_directory_includes_doctor_department(self):
        from apps.clinics.models import Department, DoctorProfile

        admin = get_user_model().objects.create_user(
            "directory.admin@example.com",
            "Directory-Admin-Secure-Passphrase-945!",
            role=get_user_model().Role.ADMIN,
        )
        doctor_user = get_user_model().objects.create_user(
            "directory.doctor@example.com",
            "Directory-Doctor-Secure-Passphrase-946!",
            role=get_user_model().Role.DOCTOR,
            first_name="Directory",
        )
        department = Department.objects.create(name="Directory Medicine")
        DoctorProfile.objects.create(
            user=doctor_user,
            department=department,
            license_number="DIR-945",
            specialization="General Practice",
        )
        self.client.force_authenticate(admin)

        response = self.client.get(reverse("accounts:staff-users"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doctor_record = next(row for row in response.data if row["id"] == doctor_user.pk)
        self.assertEqual(doctor_record["department_name"], department.name)
