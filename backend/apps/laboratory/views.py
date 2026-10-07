from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.consultations.models import Consultation
from apps.documents.models import MedicalDocument

from .models import LabTest
from .serializers import (
    LabReportCreateSerializer,
    LabReportReviewSerializer,
    LabTestCreateSerializer,
    LabTestSerializer,
)
from .services import record_lab_report, request_lab_test, review_lab_report

User = get_user_model()


class LabTestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = LabTest.objects.select_related(
            "consultation__appointment__patient__user",
            "consultation__appointment__doctor__user",
        ).prefetch_related("reports__document")
        if user.role == User.Role.ADMIN:
            return queryset
        if user.role == User.Role.DOCTOR:
            return queryset.filter(consultation__appointment__doctor__user=user)
        if user.role == User.Role.PATIENT:
            return queryset.filter(consultation__appointment__patient__user=user)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return LabTestCreateSerializer
        return LabTestSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.DOCTOR:
            raise PermissionDenied("Only doctors can request laboratory tests.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = request_lab_test(
            consultation=serializer.validated_data["consultation"],
            actor=request.user,
            name=serializer.validated_data["name"],
            clinical_question=serializer.validated_data.get("clinical_question", ""),
        )
        return Response(LabTestSerializer(test).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="reports")
    def reports(self, request, pk=None):
        test = self.get_object()
        if request.user.role not in (User.Role.DOCTOR, User.Role.ADMIN):
            raise PermissionDenied("Only the assigned doctor or an administrator can record results.")
        serializer = LabReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = None
        document_id = serializer.validated_data.get("document")
        if document_id:
            document = MedicalDocument.objects.filter(pk=document_id).first()
            if document is None or document.patient_id != test.consultation.appointment.patient_id:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"document": "Document not found for this patient."})
        report = record_lab_report(
            test=test,
            actor=request.user,
            result_text=serializer.validated_data["result_text"],
            document=document,
        )
        test.refresh_from_db()
        return Response(
            LabTestSerializer(test).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="review-report")
    def review_report(self, request, pk=None):
        if request.user.role not in (User.Role.DOCTOR, User.Role.ADMIN):
            raise PermissionDenied("Only the assigned doctor or an administrator can review results.")
        test = self.get_object()
        serializer = LabReportReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = get_object_or_404(
            test.reports,
            pk=serializer.validated_data["report"],
        )
        review_lab_report(report=report, actor=request.user)
        test.refresh_from_db()
        return Response(LabTestSerializer(test).data)
