from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.clinics.models import DoctorProfile
from apps.patients.models import PatientProfile

from .models import MedicalDocument
from .serializers import MedicalDocumentSerializer, MedicalDocumentUploadSerializer

User = get_user_model()


class MedicalDocumentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        queryset = MedicalDocument.objects.select_related(
            "patient__user",
            "appointment__doctor__user",
        )
        if user.role == User.Role.ADMIN:
            return queryset
        if user.role == User.Role.PATIENT:
            return queryset.filter(patient__user=user)
        if user.role == User.Role.DOCTOR:
            return queryset.filter(appointment__doctor__user=user)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return MedicalDocumentUploadSerializer
        return MedicalDocumentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.validated_data.get("patient")
        appointment = serializer.validated_data.get("appointment")
        if request.user.role == User.Role.PATIENT:
            own_profile = PatientProfile.objects.filter(user=request.user).first()
            if patient and patient != own_profile:
                raise PermissionDenied("You may only upload documents to your own record.")
            patient = own_profile
            if patient is None:
                raise PermissionDenied("No patient profile is linked to this account.")
        elif request.user.role == User.Role.DOCTOR:
            if not appointment or appointment.doctor.user_id != request.user.pk:
                raise PermissionDenied("Doctors must link uploads to their own appointment.")
            patient = appointment.patient
        elif request.user.role not in (User.Role.ADMIN, User.Role.RECEPTIONIST):
            raise PermissionDenied("You may not upload medical documents.")

        if patient is None:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"patient": "Select a patient for this document."})
        if appointment and appointment.patient_id != patient.pk:
            raise PermissionDenied("The appointment and patient must match.")
        document = serializer.save(patient=patient, uploaded_by=request.user)
        record_event(actor=request.user, action="medical_document.uploaded", instance=document)
        return Response(
            MedicalDocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class MedicalDocumentDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        document = get_object_or_404(
            MedicalDocument.objects.select_related(
                "patient__user",
                "appointment__doctor__user",
            ),
            pk=pk,
        )
        user = request.user
        allowed = (
            user.role == User.Role.ADMIN
            or document.patient.user_id == user.pk
            or (
                user.role == User.Role.DOCTOR
                and document.appointment_id is not None
                and document.appointment.doctor.user_id == user.pk
            )
        )
        if not allowed:
            raise PermissionDenied("You may not access this medical document.")
        response = FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.file.name.rsplit("/", 1)[-1],
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
