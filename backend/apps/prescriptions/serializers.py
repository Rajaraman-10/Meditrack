from django.utils import timezone
from rest_framework import serializers

from apps.billing.models import Invoice
from apps.consultations.models import Consultation

from .models import Medicine, Prescription, PrescriptionItem


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = (
            "id",
            "source_id",
            "name",
            "generic_name",
            "strength",
            "dosage_form",
            "route",
            "manufacturer",
        )
        read_only_fields = fields


class PrescriptionItemSerializer(serializers.ModelSerializer):
    medicine = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = PrescriptionItem
        fields = (
            "id",
            "medicine",
            "medication_name",
            "strength",
            "dosage",
            "route",
            "frequency",
            "duration",
            "instructions",
            "food_timing",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "medication_name": {"required": False},
            "strength": {"required": False},
        }

    def validate(self, attrs):
        medicine = attrs.get("medicine")
        if medicine:
            attrs["medication_name"] = medicine.name
            attrs["strength"] = medicine.strength
        elif not attrs.get("medication_name") or not attrs.get("strength"):
            raise serializers.ValidationError(
                "Select a catalog medicine or provide both medicine name and strength."
            )
        return attrs


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="consultation.appointment.patient.patient_number",
        read_only=True,
    )
    doctor_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(
        source="consultation.appointment.doctor.department.name",
        read_only=True,
    )
    patient_age = serializers.SerializerMethodField()
    patient_gender = serializers.CharField(
        source="consultation.appointment.patient.gender",
        read_only=True,
    )
    consultation_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Prescription
        fields = (
            "id",
            "consultation_id",
            "patient_number",
            "patient_name",
            "patient_age",
            "patient_gender",
            "doctor_name",
            "department_name",
            "instructions",
            "status",
            "released_at",
            "items",
            "created_at",
        )
        read_only_fields = fields

    def get_patient_name(self, obj):
        user = obj.consultation.appointment.patient.user
        return user.get_full_name() or user.email

    def get_doctor_name(self, obj):
        user = obj.consultation.appointment.doctor.user
        return user.get_full_name() or user.email

    def get_patient_age(self, obj):
        date_of_birth = obj.consultation.appointment.patient.date_of_birth
        if not date_of_birth:
            return None
        today = timezone.localdate()
        return today.year - date_of_birth.year - (
            (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
        )


class PrescriptionReleaseQueueSerializer(serializers.ModelSerializer):
    prescription_number = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    patient_number = serializers.CharField(
        source="consultation.appointment.patient.patient_number",
        read_only=True,
    )
    appointment_id = serializers.IntegerField(
        source="consultation.appointment_id",
        read_only=True,
    )
    invoice_id = serializers.SerializerMethodField()
    invoice_number = serializers.SerializerMethodField()
    invoice_status = serializers.SerializerMethodField()
    invoice_total = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    can_release = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = (
            "id",
            "prescription_number",
            "patient_name",
            "patient_number",
            "appointment_id",
            "status",
            "created_at",
            "invoice_id",
            "invoice_number",
            "invoice_status",
            "invoice_total",
            "currency",
            "can_release",
        )
        read_only_fields = fields

    def get_prescription_number(self, obj):
        return f"RX-{obj.pk:05d}"

    def get_patient_name(self, obj):
        user = obj.consultation.appointment.patient.user
        return user.get_full_name() or user.email

    def _invoice(self, obj):
        try:
            return obj.consultation.appointment.invoice
        except Invoice.DoesNotExist:
            return None

    def get_invoice_id(self, obj):
        invoice = self._invoice(obj)
        return invoice.pk if invoice else None

    def get_invoice_number(self, obj):
        invoice = self._invoice(obj)
        if not invoice:
            return None
        return f"INV-{timezone.localtime(invoice.created_at).year}-{invoice.pk:05d}"

    def get_invoice_status(self, obj):
        invoice = self._invoice(obj)
        return invoice.status if invoice else "not_generated"

    def get_invoice_total(self, obj):
        invoice = self._invoice(obj)
        if not invoice:
            return None
        return f"{invoice.total:.2f}"

    def get_currency(self, obj):
        invoice = self._invoice(obj)
        return invoice.currency if invoice else "INR"

    def get_can_release(self, obj):
        invoice = self._invoice(obj)
        return bool(invoice and invoice.status == Invoice.Status.PAID)


class PrescriptionCreateSerializer(serializers.Serializer):
    consultation = serializers.PrimaryKeyRelatedField(
        queryset=Consultation.objects.select_related("appointment__doctor__user")
    )
    instructions = serializers.CharField(required=False, allow_blank=True)
    items = PrescriptionItemSerializer(many=True, allow_empty=False)
