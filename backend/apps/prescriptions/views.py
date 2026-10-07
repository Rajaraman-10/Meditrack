from django.contrib.auth import get_user_model
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status

from apps.consultations.models import Consultation

from .models import Medicine, Prescription
from .serializers import (
    MedicineSerializer,
    PrescriptionCreateSerializer,
    PrescriptionReleaseQueueSerializer,
    PrescriptionSerializer,
)
from .services import create_prescription, release_prescription

User = get_user_model()


class PrescriptionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = Prescription.objects.select_related(
            "consultation__appointment__patient__user",
            "consultation__appointment__doctor__user",
            "consultation__appointment__doctor__department",
        ).prefetch_related("items")
        if user.role == User.Role.ADMIN:
            return queryset
        if user.role == User.Role.DOCTOR:
            return queryset.filter(consultation__appointment__doctor__user=user)
        if user.role == User.Role.PATIENT:
            return queryset.filter(
                consultation__appointment__patient__user=user,
                status=Prescription.Status.RELEASED,
            )
        if user.role == User.Role.BILLING:
            return queryset.filter(status=Prescription.Status.RELEASED)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Role.DOCTOR:
            raise PermissionDenied("Only doctors can create prescriptions.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription = create_prescription(
            consultation=serializer.validated_data["consultation"],
            doctor_user=request.user,
            items=serializer.validated_data["items"],
            instructions=serializer.validated_data.get("instructions", ""),
        )
        return Response(
            PrescriptionSerializer(prescription).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="release-queue")
    def release_queue(self, request):
        if request.user.role not in (User.Role.ADMIN, User.Role.BILLING):
            raise PermissionDenied("Only billing staff can view pending prescription releases.")
        queryset = Prescription.objects.select_related(
            "consultation__appointment__patient__user",
            "consultation__appointment__invoice",
        ).filter(status=Prescription.Status.PAYMENT_PENDING).order_by("created_at")
        return Response(PrescriptionReleaseQueueSerializer(queryset, many=True).data)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        if request.user.role not in (User.Role.ADMIN, User.Role.BILLING):
            raise PermissionDenied("Only billing staff can release prescriptions.")
        prescription = release_prescription(
            prescription_id=pk,
            actor=request.user,
        )
        return Response(PrescriptionSerializer(prescription).data)


class MedicineViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MedicineSerializer
    pagination_class = None
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        queryset = Medicine.objects.filter(is_active=True)
        search = self.request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(generic_name__icontains=search)
                | Q(strength__icontains=search)
            )
        return queryset[:20]
