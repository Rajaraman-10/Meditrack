from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Department, DoctorAvailability, DoctorProfile, ScheduleException

User = get_user_model()


class ClinicApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "admin@example.com",
            "Clinic-Admin-Passphrase-718!",
            role=User.Role.ADMIN,
        )
        self.receptionist = User.objects.create_user(
            "reception@example.com",
            "Clinic-Reception-Passphrase-719!",
            role=User.Role.RECEPTIONIST,
        )
        self.patient = User.objects.create_user(
            "patient@example.com",
            "Clinic-Patient-Passphrase-720!",
            role=User.Role.PATIENT,
        )
        self.department = Department.objects.create(name="Family Medicine")
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Clinic-Doctor-Passphrase-721!",
            role=User.Role.DOCTOR,
            first_name="Jordan",
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=self.department,
            license_number="LIC-100",
            specialization="Family Medicine",
            slot_duration_minutes=30,
        )

    def test_admin_can_manage_departments_and_create_doctor(self):
        self.client.force_authenticate(self.admin)
        department_response = self.client.post(
            reverse("department-list"),
            {"name": "Pediatrics", "description": "Children's health"},
            format="json",
        )
        doctor_response = self.client.post(
            reverse("doctor-list"),
            {
                "email": "new.doctor@example.com",
                "password": "New-Doctor-Passphrase-722!",
                "first_name": "New",
                "last_name": "Doctor",
                "department": self.department.pk,
                "license_number": "LIC-101",
                "specialization": "Cardiology",
                "slot_duration_minutes": 45,
            },
            format="json",
        )

        self.assertEqual(department_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(department_response.data["code"], "PEDIATRICS")
        self.assertEqual(doctor_response.status_code, status.HTTP_201_CREATED)
        created_doctor = DoctorProfile.objects.get(license_number="LIC-101")
        self.assertEqual(created_doctor.user.role, User.Role.DOCTOR)
        self.assertEqual(created_doctor.slot_duration_minutes, 45)

    def test_admin_can_deactivate_department_and_public_directory_hides_it(self):
        self.client.force_authenticate(self.admin)
        updated = self.client.patch(
            reverse("department-detail", args=(self.department.pk,)),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertFalse(updated.data["is_active"])

        self.client.force_authenticate(self.patient)
        directory = self.client.get(reverse("department-list"))
        self.assertEqual(directory.status_code, status.HTTP_200_OK)
        self.assertFalse(any(row["id"] == self.department.pk for row in directory.data))

    def test_patient_can_read_but_not_write_clinic_catalog(self):
        self.client.force_authenticate(self.patient)

        list_response = self.client.get(reverse("doctor-list"))
        create_response = self.client.post(
            reverse("department-list"),
            {"name": "Unauthorized department"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_can_manage_schedule_and_doctor_can_manage_own(self):
        self.client.force_authenticate(self.receptionist)
        schedule_response = self.client.post(
            reverse("availability-list"),
            {
                "doctor": self.doctor.pk,
                "weekday": 0,
                "start_time": "09:00:00",
                "end_time": "12:00:00",
            },
            format="json",
        )
        self.assertEqual(schedule_response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(self.doctor_user)
        own_schedule = self.client.post(
            reverse("availability-list"),
            {
                "doctor": self.doctor.pk,
                "weekday": 1,
                "start_time": "10:00:00",
                "end_time": "13:00:00",
            },
            format="json",
        )
        self.assertEqual(own_schedule.status_code, status.HTTP_201_CREATED)

    def test_doctor_can_update_and_remove_own_weekly_availability(self):
        availability = DoctorAvailability.objects.create(
            doctor=self.doctor,
            weekday=2,
            start_time="09:00",
            end_time="12:00",
        )
        self.client.force_authenticate(self.doctor_user)

        update_response = self.client.patch(
            reverse("availability-detail", args=(availability.pk,)),
            {"start_time": "10:00", "end_time": "14:00"},
            format="json",
        )
        availability.refresh_from_db()
        delete_response = self.client.delete(
            reverse("availability-detail", args=(availability.pk,))
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(availability.start_time.strftime("%H:%M"), "10:00")
        self.assertEqual(availability.end_time.strftime("%H:%M"), "14:00")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DoctorAvailability.objects.filter(pk=availability.pk).exists())

    def test_doctor_can_add_and_update_date_specific_availability(self):
        target_date = timezone.localdate() + timedelta(days=10)
        self.client.force_authenticate(self.doctor_user)

        create_response = self.client.post(
            reverse("schedule-exception-list"),
            {
                "doctor": self.doctor.pk,
                "date": target_date.isoformat(),
                "is_closed": False,
                "start_time": "11:00:00",
                "end_time": "15:00:00",
                "note": "Clinic session",
            },
            format="json",
        )
        exception = ScheduleException.objects.get(doctor=self.doctor, date=target_date)
        update_response = self.client.patch(
            reverse("schedule-exception-detail", args=(exception.pk,)),
            {"start_time": "12:00:00", "end_time": "16:00:00"},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        exception.refresh_from_db()
        self.assertEqual(exception.start_time.strftime("%H:%M"), "12:00")
        self.assertEqual(exception.end_time.strftime("%H:%M"), "16:00")

    def test_doctor_cannot_change_another_doctors_schedule(self):
        other_user = User.objects.create_user(
            "other.doctor@example.com",
            "Other-Doctor-Passphrase-723!",
            role=User.Role.DOCTOR,
        )
        other_doctor = DoctorProfile.objects.create(
            user=other_user,
            department=self.department,
            license_number="LIC-102",
            specialization="Pediatrics",
        )
        self.client.force_authenticate(self.doctor_user)

        response = self.client.post(
            reverse("availability-list"),
            {
                "doctor": other_doctor.pk,
                "weekday": 0,
                "start_time": "09:00:00",
                "end_time": "12:00:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_rejects_overlapping_windows_and_exceptions_override_weekly_hours(self):
        target_date = timezone.localdate() + timedelta(days=7)
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            weekday=target_date.weekday(),
            start_time="09:00",
            end_time="12:00",
        )
        self.client.force_authenticate(self.receptionist)

        overlap = self.client.post(
            reverse("availability-list"),
            {
                "doctor": self.doctor.pk,
                "weekday": target_date.weekday(),
                "start_time": "11:00:00",
                "end_time": "13:00:00",
            },
            format="json",
        )
        exception = self.client.post(
            reverse("schedule-exception-list"),
            {
                "doctor": self.doctor.pk,
                "date": target_date.isoformat(),
                "is_closed": True,
                "note": "Doctor on leave",
            },
            format="json",
        )
        slots_response = self.client.get(
            reverse("doctor-slots", args=(self.doctor.pk,)),
            {"date": target_date.isoformat()},
        )

        self.assertEqual(overlap.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(exception.status_code, status.HTTP_201_CREATED)
        self.assertEqual(slots_response.status_code, status.HTTP_200_OK)
        self.assertEqual(slots_response.data["slots"], [])
        self.assertTrue(ScheduleException.objects.filter(doctor=self.doctor).exists())
