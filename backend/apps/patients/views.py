from django.contrib.auth import get_user_model
from rest_framework import generics, serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrReceptionist
from apps.appointments.models import Appointment
from apps.appointments.serializers import AppointmentSerializer
from apps.audit.models import AuditLog
from apps.consultations.models import Consultation
from apps.consultations.serializers import ConsultationSerializer
from apps.documents.models import MedicalDocument
from apps.documents.serializers import MedicalDocumentSerializer
from apps.laboratory.models import LabTest
from apps.laboratory.serializers import LabTestSerializer
from apps.prescriptions.models import Prescription
from apps.prescriptions.serializers import PrescriptionSerializer

from .models import PatientProfile
from .serializers import PatientCreateSerializer, PatientProfileSerializer

User = get_user_model()


class DoctorPatientSummarySerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = PatientProfile
        fields = (
            "id",
            "patient_number",
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "blood_group",
        )
        read_only_fields = fields


def _audit_patient_access(user, action, patient, result):
    AuditLog.objects.create(
        actor=user,
        action=action,
        object_type="patients.patientprofile",
        object_id=str(patient.pk) if patient else "unresolved",
        metadata={"result": result},
    )


def _doctor_can_access_patient(user, patient):
    return Appointment.objects.filter(
        patient=patient,
        doctor__user=user,
    ).exclude(status=Appointment.Status.CANCELLED).exists()


class DoctorPatientSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.DOCTOR:
            raise PermissionDenied("Only doctors may search patient records.")

        patient_number = request.query_params.get("patient_number", "").strip().upper()
        if not patient_number:
            raise serializers.ValidationError(
                {"patient_number": "Enter a patient number to search."}
            )

        patient = (
            PatientProfile.objects.select_related("user")
            .filter(patient_number=patient_number, user__is_active=True)
            .first()
        )
        if not patient:
            _audit_patient_access(request.user, "patient.search", None, "not_found")
            raise NotFound("No accessible patient was found for that patient number.")

        if not _doctor_can_access_patient(request.user, patient):
            _audit_patient_access(request.user, "patient.search", patient, "not_authorized")
            raise NotFound("No accessible patient was found for that patient number.")

        _audit_patient_access(request.user, "patient.search", patient, "authorized")
        return Response(DoctorPatientSummarySerializer(patient).data)


class DoctorPatientRecordView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.role != User.Role.DOCTOR:
            raise PermissionDenied("Only doctors may view patient records.")

        patient = (
            PatientProfile.objects.select_related("user")
            .filter(pk=pk, user__is_active=True)
            .first()
        )
        if not patient:
            _audit_patient_access(request.user, "patient.record_viewed", None, "not_found")
            raise NotFound("No accessible patient record was found.")

        if not _doctor_can_access_patient(request.user, patient):
            _audit_patient_access(
                request.user,
                "patient.record_viewed",
                patient,
                "not_authorized",
            )
            raise NotFound("No accessible patient record was found.")

        _audit_patient_access(
            request.user,
            "patient.record_viewed",
            patient,
            "authorized",
        )
        appointments = Appointment.objects.filter(
            patient=patient,
            doctor__user=request.user,
        ).select_related("patient__user", "doctor__user", "doctor__department")
        consultations = Consultation.objects.filter(
            appointment__patient=patient,
            appointment__doctor__user=request.user,
        ).select_related(
            "appointment__patient__user",
            "appointment__doctor__user",
            "appointment__doctor__department",
        ).prefetch_related("notes")
        return Response(
            {
                "patient": DoctorPatientSummarySerializer(patient).data,
                "appointments": AppointmentSerializer(appointments, many=True).data,
                "consultations": ConsultationSerializer(consultations, many=True).data,
                "prescriptions": PrescriptionSerializer(
                    Prescription.objects.filter(
                        consultation__appointment__patient=patient,
                        consultation__appointment__doctor__user=request.user,
                    ).select_related(
                        "consultation__appointment__patient__user",
                        "consultation__appointment__doctor__user",
                    ).prefetch_related("items"),
                    many=True,
                ).data,
                "lab_tests": LabTestSerializer(
                    LabTest.objects.filter(
                        consultation__appointment__patient=patient,
                        consultation__appointment__doctor__user=request.user,
                    ).select_related(
                        "consultation__appointment__patient__user",
                        "consultation__appointment__doctor__user",
                    ).prefetch_related("reports__reported_by", "reports__document"),
                    many=True,
                ).data,
                "documents": MedicalDocumentSerializer(
                    MedicalDocument.objects.filter(
                        patient=patient,
                        appointment__doctor__user=request.user,
                    ).select_related("patient", "appointment"),
                    many=True,
                ).data,
            }
        )


class PatientListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = PatientProfile.objects.select_related("user")
        if user.role in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            return queryset
        if user.role == User.Role.PATIENT:
            return queryset.filter(user=user)
        raise PermissionDenied("Doctors do not have patient-list access in this phase.")

    def get_serializer_class(self):
        if self.request.method == "POST":
            if self.request.user.role not in (User.Role.ADMIN, User.Role.RECEPTIONIST):
                raise PermissionDenied("Only clinic staff can register another patient.")
            return PatientCreateSerializer
        return PatientProfileSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(
            PatientProfileSerializer(patient).data,
            status=201,
        )


class PatientDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PatientProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = PatientProfile.objects.select_related("user")
        if user.role in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            return queryset
        if user.role == User.Role.PATIENT:
            return queryset.filter(user=user)
        return queryset.none()

    def get_serializer(self, *args, **kwargs):
        if self.request.method in ("PUT", "PATCH") and self.request.user.role not in (
            User.Role.ADMIN,
            User.Role.RECEPTIONIST,
            User.Role.PATIENT,
        ):
            raise PermissionDenied("You may not update patient details.")
        return super().get_serializer(*args, **kwargs)
