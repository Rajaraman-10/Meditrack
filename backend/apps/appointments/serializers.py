from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.clinics.models import DoctorProfile
from apps.patients.models import PatientProfile

from .models import Appointment, QueueEntry

User = get_user_model()


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="patient.patient_number",
        read_only=True,
    )
    patient_email = serializers.EmailField(source="patient.user.email", read_only=True)
    doctor_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(
        source="doctor.department.name",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = (
            "id",
            "patient",
                "patient_number",
                "patient_name",
            "patient_email",
            "doctor",
            "doctor_name",
            "department_name",
            "starts_at",
            "ends_at",
            "status",
            "reason",
            "created_at",
        )
        read_only_fields = fields

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name() or obj.patient.user.email

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.email


class AppointmentCreateSerializer(serializers.Serializer):
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=DoctorProfile.objects.filter(
            user__is_active=True,
            department__is_active=True,
            is_accepting_appointments=True,
        )
    )
    starts_at = serializers.DateTimeField()
    patient = serializers.PrimaryKeyRelatedField(
        queryset=PatientProfile.objects.select_related("user"),
        required=False,
    )
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        actor = self.context["request"].user
        patient = attrs.get("patient")
        if actor.role == User.Role.PATIENT:
            if patient and patient.user_id != actor.pk:
                raise serializers.ValidationError(
                    {"patient": "Patients may only book appointments for themselves."}
                )
        elif actor.role in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            if patient is None:
                raise serializers.ValidationError(
                    {"patient": "Clinic staff must select a patient."}
                )
        else:
            raise serializers.ValidationError(
                "Only patients and clinic staff can book appointments."
            )
        attrs["patient"] = patient or PatientProfile.objects.get(user=actor)
        return attrs


class AppointmentUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Appointment.Status.choices, required=False)
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=DoctorProfile.objects.filter(
            user__is_active=True,
            department__is_active=True,
            is_accepting_appointments=True,
        ),
        required=False,
    )
    starts_at = serializers.DateTimeField(required=False)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class QueueEntrySerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    appointment_status = serializers.CharField(source="appointment.status", read_only=True)

    class Meta:
        model = QueueEntry
        fields = (
            "id",
            "appointment",
            "patient_name",
            "doctor_name",
            "queue_date",
            "position",
            "status",
            "appointment_status",
            "checked_in_at",
        )
        read_only_fields = fields

    def get_patient_name(self, obj):
        return obj.appointment.patient.user.get_full_name() or obj.appointment.patient.user.email

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.email


class QueueEntryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueEntry
        fields = ("status",)
