from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Consultation, ConsultationNote

User = get_user_model()


class ConsultationNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = ConsultationNote
        fields = ("id", "author_name", "body", "created_at")
        read_only_fields = ("id", "author_name", "created_at")

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.email


class ConsultationSerializer(serializers.ModelSerializer):
    appointment_id = serializers.IntegerField(read_only=True)
    patient_number = serializers.CharField(
        source="appointment.patient.patient_number",
        read_only=True,
    )
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    appointment_starts_at = serializers.DateTimeField(
        source="appointment.starts_at",
        read_only=True,
    )
    notes = ConsultationNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = (
            "id",
            "appointment_id",
            "patient_number",
            "patient_name",
            "doctor_name",
            "appointment_starts_at",
            "diagnosis",
            "clinical_notes",
            "follow_up_date",
            "status",
            "started_at",
            "completed_at",
            "notes",
        )
        read_only_fields = (
            "id",
            "appointment_id",
            "patient_name",
            "doctor_name",
            "appointment_starts_at",
            "status",
            "started_at",
            "completed_at",
            "notes",
        )

    def get_patient_name(self, obj):
        return obj.appointment.patient.user.get_full_name() or obj.appointment.patient.user.email

    def get_doctor_name(self, obj):
        return obj.appointment.doctor.user.get_full_name() or obj.appointment.doctor.user.email


class ConsultationStartSerializer(serializers.Serializer):
    appointment = serializers.IntegerField()


class ConsultationNoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationNote
        fields = ("body",)
