from rest_framework import serializers

from apps.consultations.models import Consultation
from apps.documents.serializers import MedicalDocumentSerializer

from .models import LabReport, LabTest


class LabReportSerializer(serializers.ModelSerializer):
    document = MedicalDocumentSerializer(read_only=True)
    reported_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LabReport
        fields = ("id", "result_text", "document", "reported_by_name", "reported_at", "reviewed_at")
        read_only_fields = fields

    def get_reported_by_name(self, obj):
        return obj.reported_by.get_full_name() or obj.reported_by.email


class LabTestSerializer(serializers.ModelSerializer):
    reports = LabReportSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="consultation.appointment.patient.patient_number",
        read_only=True,
    )
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = LabTest
        fields = (
            "id",
            "consultation",
            "appointment_id",
            "patient_id",
            "patient_number",
            "name",
            "clinical_question",
            "status",
            "requested_at",
            "patient_name",
            "doctor_name",
            "reports",
        )
        read_only_fields = fields

    appointment_id = serializers.IntegerField(
        source="consultation.appointment_id",
        read_only=True,
    )
    patient_id = serializers.IntegerField(
        source="consultation.appointment.patient_id",
        read_only=True,
    )

    def get_patient_name(self, obj):
        user = obj.consultation.appointment.patient.user
        return user.get_full_name() or user.email

    def get_doctor_name(self, obj):
        user = obj.consultation.appointment.doctor.user
        return user.get_full_name() or user.email


class LabTestCreateSerializer(serializers.Serializer):
    consultation = serializers.PrimaryKeyRelatedField(queryset=Consultation.objects.all())
    name = serializers.CharField(max_length=180)
    clinical_question = serializers.CharField(required=False, allow_blank=True)


class LabReportCreateSerializer(serializers.Serializer):
    result_text = serializers.CharField(allow_blank=True)
    document = serializers.IntegerField(required=False, allow_null=True)


class LabReportReviewSerializer(serializers.Serializer):
    report = serializers.IntegerField()
