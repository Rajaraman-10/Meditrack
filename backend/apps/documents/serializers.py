from rest_framework import serializers

from apps.patients.models import PatientProfile

from .models import MedicalDocument


class MedicalDocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="patient.patient_number",
        read_only=True,
    )

    class Meta:
        model = MedicalDocument
        fields = (
            "id",
            "patient",
            "patient_number",
            "appointment",
            "title",
            "category",
            "file_name",
            "uploaded_at",
        )
        read_only_fields = ("id", "patient", "file_name", "uploaded_at")

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1]


class MedicalDocumentUploadSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(
        queryset=PatientProfile.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MedicalDocument
        fields = ("id", "patient", "appointment", "title", "category", "file")
        read_only_fields = ("id",)
