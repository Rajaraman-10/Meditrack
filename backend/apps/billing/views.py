from django.contrib.auth import get_user_model
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.appointments.models import Appointment

from .models import Invoice
from .serializers import (
    InvoiceCreateSerializer,
    InvoiceSerializer,
    InvoiceStatusSerializer,
    UnbilledAppointmentSerializer,
)
from .services import change_invoice_status, create_invoice

User = get_user_model()


class InvoiceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = Invoice.objects.select_related(
            "appointment__patient__user",
            "appointment__doctor__user",
            "appointment__doctor__department",
            "created_by",
        ).prefetch_related("items")
        if user.role in (
            User.Role.ADMIN,
            User.Role.RECEPTIONIST,
            User.Role.BILLING,
        ):
            return queryset
        if user.role == User.Role.PATIENT:
            return queryset.filter(appointment__patient__user=user)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in (
            User.Role.ADMIN,
            User.Role.RECEPTIONIST,
            User.Role.BILLING,
        ):
            raise PermissionDenied("Only clinic staff can create invoices.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = create_invoice(
            appointment=serializer.validated_data["appointment"],
            actor=request.user,
            items=serializer.validated_data["items"],
            currency=serializer.validated_data.get("currency", "INR"),
            discount_amount=serializer.validated_data.get(
                "discount_amount",
                0,
            ),
        )
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["get"],
        url_path="unbilled-appointments",
        pagination_class=None,
    )
    def unbilled_appointments(self, request):
        if request.user.role not in (
            User.Role.ADMIN,
            User.Role.RECEPTIONIST,
            User.Role.BILLING,
        ):
            raise PermissionDenied("You may not view billable appointments.")
        appointments = Appointment.objects.select_related(
            "patient__user",
            "doctor__user",
        ).filter(
            status__in=(
                Appointment.Status.IN_CONSULTATION,
                Appointment.Status.COMPLETED,
            ),
            invoice__isnull=True,
        ).order_by("-starts_at")
        return Response(UnbilledAppointmentSerializer(appointments, many=True).data)

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        if request.user.role not in (
            User.Role.ADMIN,
            User.Role.RECEPTIONIST,
            User.Role.BILLING,
        ):
            raise PermissionDenied("Only clinic staff can update invoice status.")
        invoice = self.get_object()
        serializer = InvoiceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = change_invoice_status(
            invoice=invoice,
            actor=request.user,
            status=serializer.validated_data["status"],
            payment_method=serializer.validated_data.get("payment_method"),
            transaction_reference=serializer.validated_data.get(
                "transaction_reference",
                "",
            ),
        )
        return Response(InvoiceSerializer(invoice).data)
