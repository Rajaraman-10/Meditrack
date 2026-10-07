from django.utils import timezone
from rest_framework import serializers

from apps.appointments.models import Appointment

from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ("id", "description", "quantity", "unit_price")
        read_only_fields = ("id",)


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    invoice_number = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="appointment.patient.patient_number",
        read_only=True,
    )
    patient_age = serializers.SerializerMethodField()
    patient_gender = serializers.CharField(
        source="appointment.patient.gender",
        read_only=True,
    )
    doctor_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(
        source="appointment.doctor.department.name",
        read_only=True,
    )
    consultation_date = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    appointment_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "appointment_id",
            "patient_number",
            "patient_name",
            "patient_age",
            "patient_gender",
            "doctor_name",
            "department_name",
            "consultation_date",
            "status",
            "currency",
            "items",
            "subtotal",
            "discount_amount",
            "total",
            "payment_method",
            "transaction_reference",
            "issued_at",
            "paid_at",
            "created_at",
            "created_by_name",
        )
        read_only_fields = fields

    def get_patient_name(self, obj):
        user = obj.appointment.patient.user
        return user.get_full_name() or user.email

    def get_doctor_name(self, obj):
        user = obj.appointment.doctor.user
        return user.get_full_name() or user.email

    def get_invoice_number(self, obj):
        invoice_year = timezone.localtime(obj.created_at).year
        return f"INV-{invoice_year}-{obj.pk:05d}"

    def get_patient_age(self, obj):
        date_of_birth = obj.appointment.patient.date_of_birth
        if not date_of_birth:
            return None
        appointment_date = timezone.localtime(obj.appointment.starts_at).date()
        return (
            appointment_date.year
            - date_of_birth.year
            - (
                (appointment_date.month, appointment_date.day)
                < (date_of_birth.month, date_of_birth.day)
            )
        )

    def get_consultation_date(self, obj):
        return timezone.localtime(obj.appointment.starts_at).date()

    def get_created_by_name(self, obj):
        user = obj.created_by
        return user.get_full_name() or user.email


class InvoiceCreateSerializer(serializers.Serializer):
    appointment = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.select_related("patient__user", "doctor__user")
    )
    currency = serializers.RegexField(regex=r"^[A-Za-z]{3}$", required=False, default="INR")
    discount_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        default=0,
    )
    items = InvoiceItemSerializer(many=True, allow_empty=False)


class InvoiceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Invoice.Status.choices)
    payment_method = serializers.ChoiceField(
        choices=Invoice.PaymentMethod.choices,
        required=False,
    )
    transaction_reference = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        if (
            attrs["status"] == Invoice.Status.PAID
            and not attrs.get("payment_method")
        ):
            raise serializers.ValidationError(
                {"payment_method": "Choose how the patient paid."}
            )
        return attrs


class UnbilledAppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="patient.patient_number",
        read_only=True,
    )
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ("id", "starts_at", "patient_name", "patient_number", "doctor_name")
        read_only_fields = fields

    def get_patient_name(self, obj):
        user = obj.patient.user
        return user.get_full_name() or user.email

    def get_doctor_name(self, obj):
        user = obj.doctor.user
        return user.get_full_name() or user.email
