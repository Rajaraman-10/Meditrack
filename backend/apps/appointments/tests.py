from datetime import datetime, time, timedelta, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinics.models import Department, DoctorAvailability, DoctorProfile
from apps.patients.models import PatientProfile

from .models import Appointment, QueueEntry

User = get_user_model()


class AppointmentAndQueueApiTests(APITestCase):
    def setUp(self):
        self.patient_user = User.objects.create_user(
            "patient@example.com",
            "Appointment-Patient-Passphrase-718!",
            role=User.Role.PATIENT,
            first_name="Pat",
        )
        self.patient = PatientProfile.objects.create(user=self.patient_user)
        self.other_patient_user = User.objects.create_user(
            "other.patient@example.com",
            "Appointment-Patient-Passphrase-719!",
            role=User.Role.PATIENT,
        )
        self.other_patient = PatientProfile.objects.create(
            user=self.other_patient_user
        )
        self.receptionist = User.objects.create_user(
            "reception@example.com",
            "Appointment-Reception-Passphrase-720!",
            role=User.Role.RECEPTIONIST,
        )
        self.doctor_user = User.objects.create_user(
            "doctor@example.com",
            "Appointment-Doctor-Passphrase-721!",
            role=User.Role.DOCTOR,
            first_name="Doc",
        )
        department = Department.objects.create(name="General Practice")
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user,
            department=department,
            license_number="APPT-100",
            specialization="General Practice",
            slot_duration_minutes=30,
        )
        self.booking_date = timezone.localdate() + timedelta(days=3)
        DoctorAvailability.objects.create(
            doctor=self.doctor,
            weekday=self.booking_date.weekday(),
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        self.first_slot = timezone.make_aware(
            datetime.combine(self.booking_date, time(9, 0)),
            timezone.get_default_timezone(),
        )
        self.second_slot = timezone.make_aware(
            datetime.combine(self.booking_date, time(9, 30)),
            timezone.get_default_timezone(),
        )

    def _book(self, *, user=None, patient=None, starts_at=None):
        self.client.force_authenticate(user or self.patient_user)
        payload = {
            "doctor": self.doctor.pk,
            "starts_at": (starts_at or self.first_slot).isoformat(),
        }
        if patient is not None:
            payload["patient"] = patient.pk
        return self.client.post(
            reverse("appointment-list"),
            payload,
            format="json",
        )

    def test_patient_can_list_slots_and_book_an_available_slot(self):
        self.client.force_authenticate(self.patient_user)
        slots_response = self.client.get(
            reverse("doctor-slots", args=(self.doctor.pk,)),
            {"date": self.booking_date.isoformat()},
        )
        booking_response = self._book()

        self.assertEqual(slots_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(slots_response.data["slots"]), 6)
        self.assertEqual(slots_response.data["slot_duration_minutes"], 30)
        self.assertEqual(booking_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(booking_response.data["status"], Appointment.Status.SCHEDULED)
        self.assertEqual(
            booking_response.data["ends_at"],
            (self.first_slot + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
        )

    def test_backend_rejects_double_booking_and_non_slot_times(self):
        first_booking = self._book()
        second_booking = self._book(user=self.other_patient_user, starts_at=self.first_slot)
        off_grid_booking = self._book(
            user=self.other_patient_user,
            starts_at=self.first_slot + timedelta(minutes=15),
        )

        self.assertEqual(first_booking.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_booking.status_code, 409)
        self.assertEqual(off_grid_booking.status_code, 409)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_patient_cannot_book_for_another_patient(self):
        response = self._book(patient=self.other_patient)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_patient_sees_only_own_appointments_and_can_cancel_own_booking(self):
        booking = self._book()
        appointment_id = booking.data["id"]
        self.client.force_authenticate(self.other_patient_user)
        hidden = self.client.get(
            reverse("appointment-detail", args=(appointment_id,))
        )
        self.client.force_authenticate(self.patient_user)
        list_response = self.client.get(reverse("appointment-list"))
        cancellation = self.client.patch(
            reverse("appointment-detail", args=(appointment_id,)),
            {"status": Appointment.Status.CANCELLED},
            format="json",
        )

        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(cancellation.status_code, status.HTTP_200_OK)
        self.assertEqual(cancellation.data["status"], Appointment.Status.CANCELLED)

    def test_doctor_sees_only_appointments_assigned_to_them(self):
        own_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at=self.first_slot,
            ends_at=self.first_slot + timedelta(minutes=30),
        )
        other_doctor_user = User.objects.create_user(
            "other.doctor@example.com",
            "Appointment-Other-Doctor-Passphrase-722!",
            role=User.Role.DOCTOR,
        )
        other_doctor = DoctorProfile.objects.create(
            user=other_doctor_user,
            department=self.doctor.department,
            license_number="APPT-101",
            specialization="General Practice",
        )
        Appointment.objects.create(
            patient=self.other_patient,
            doctor=other_doctor,
            starts_at=self.second_slot,
            ends_at=self.second_slot + timedelta(minutes=30),
        )
        self.client.force_authenticate(self.doctor_user)

        response = self.client.get(reverse("appointment-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [own_appointment.pk])

    def test_doctor_cannot_cancel_or_reschedule_appointments(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at=self.first_slot,
            ends_at=self.first_slot + timedelta(minutes=30),
        )
        self.client.force_authenticate(self.doctor_user)

        response = self.client.patch(
            reverse("appointment-detail", args=(appointment.pk,)),
            {"status": Appointment.Status.CANCELLED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_can_book_for_patient_and_reschedule(self):
        booking = self._book(
            user=self.receptionist,
            patient=self.patient,
        )
        self.assertEqual(booking.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse("appointment-detail", args=(booking.data["id"],)),
            {
                "doctor": self.doctor.pk,
                "starts_at": self.second_slot.isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["starts_at"], self.second_slot.isoformat().replace("+00:00", "Z"))

    def test_receptionist_check_in_creates_ordered_queue_entries(self):
        today = timezone.localdate()
        first_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at=timezone.make_aware(
                datetime.combine(today, time(9, 0)),
                timezone.get_default_timezone(),
            ),
            ends_at=timezone.make_aware(
                datetime.combine(today, time(9, 30)),
                timezone.get_default_timezone(),
            ),
            created_by=self.receptionist,
        )
        second_appointment = Appointment.objects.create(
            patient=self.other_patient,
            doctor=self.doctor,
            starts_at=timezone.make_aware(
                datetime.combine(today, time(9, 30)),
                timezone.get_default_timezone(),
            ),
            ends_at=timezone.make_aware(
                datetime.combine(today, time(10, 0)),
                timezone.get_default_timezone(),
            ),
            created_by=self.receptionist,
        )
        self.client.force_authenticate(self.receptionist)

        first_checkin = self.client.post(
            reverse("appointment-check-in", args=(first_appointment.pk,)),
            format="json",
        )
        second_checkin = self.client.post(
            reverse("appointment-check-in", args=(second_appointment.pk,)),
            format="json",
        )
        queue_response = self.client.get(reverse("queue-list"))

        self.assertEqual(first_checkin.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_checkin.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first_checkin.data["position"], 1)
        self.assertEqual(second_checkin.data["position"], 2)
        self.assertEqual(len(queue_response.data), 2)
        self.assertEqual(
            Appointment.objects.get(pk=first_appointment.pk).status,
            Appointment.Status.CHECKED_IN,
        )

    def test_check_in_uses_clinic_local_date_across_utc_midnight(self):
        today = timezone.localdate()
        starts_at = timezone.make_aware(
            datetime.combine(today, time(0, 15)),
            timezone.get_default_timezone(),
        )
        self.assertNotEqual(
            starts_at.astimezone(datetime_timezone.utc).date(),
            today,
        )
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
        )
        self.client.force_authenticate(self.receptionist)

        response = self.client.post(
            reverse("appointment-check-in", args=(appointment.pk,)),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["queue_date"], today.isoformat())

    def test_only_staff_can_check_in_or_manage_the_queue(self):
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            starts_at=timezone.make_aware(
                datetime.combine(timezone.localdate(), time(9, 0)),
                timezone.get_default_timezone(),
            ),
            ends_at=timezone.make_aware(
                datetime.combine(timezone.localdate(), time(9, 30)),
                timezone.get_default_timezone(),
            ),
        )
        queue_entry = QueueEntry.objects.create(
            appointment=appointment,
            doctor=self.doctor,
            queue_date=timezone.localdate(),
            position=1,
        )
        self.client.force_authenticate(self.patient_user)

        checkin = self.client.post(
            reverse("appointment-check-in", args=(appointment.pk,)),
            format="json",
        )
        queue_update = self.client.patch(
            reverse("queue-detail", args=(queue_entry.pk,)),
            {"status": QueueEntry.Status.LEFT},
            format="json",
        )

        self.assertEqual(checkin.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(queue_update.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(QueueEntry.objects.count(), 1)
