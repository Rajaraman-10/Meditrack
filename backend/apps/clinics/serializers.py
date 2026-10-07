from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.accounts.serializers import NormalizedEmailField

from .models import Department, DoctorAvailability, DoctorProfile, ScheduleException

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    code = serializers.RegexField(
        regex=r"^[A-Za-z0-9][A-Za-z0-9_-]{1,23}$",
        required=False,
    )

    class Meta:
        model = Department
        fields = ("id", "name", "code", "description", "is_active", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_code(self, value):
        normalized = value.strip().upper()
        queryset = Department.objects.filter(code__iexact=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A department with this code already exists.")
        return normalized


class DoctorProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = DoctorProfile
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "department",
            "department_name",
            "license_number",
            "specialization",
            "phone",
            "consultation_fee",
            "slot_duration_minutes",
            "bio",
            "is_accepting_appointments",
        )
        read_only_fields = ("id", "email", "first_name", "last_name", "department_name")

    def validate_slot_duration_minutes(self, value):
        if value < 5 or value > 240:
            raise serializers.ValidationError("Slot duration must be between 5 and 240 minutes.")
        return value


class DoctorCreateSerializer(serializers.Serializer):
    email = NormalizedEmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.filter(is_active=True))
    license_number = serializers.CharField(
        max_length=80,
        validators=[UniqueValidator(queryset=DoctorProfile.objects.all())],
    )
    specialization = serializers.CharField(max_length=160)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    consultation_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False, default=0
    )
    slot_duration_minutes = serializers.IntegerField(
        min_value=5, max_value=240, required=False, default=30
    )
    bio = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data.pop("email"),
                password=validated_data.pop("password"),
                first_name=validated_data.pop("first_name"),
                last_name=validated_data.pop("last_name"),
                role=User.Role.DOCTOR,
            )
            return DoctorProfile.objects.create(user=user, **validated_data)


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = DoctorAvailability
        fields = (
            "id",
            "doctor",
            "weekday",
            "weekday_label",
            "start_time",
            "end_time",
            "is_active",
        )
        read_only_fields = ("id", "weekday_label")

    def validate(self, attrs):
        doctor = attrs.get("doctor", getattr(self.instance, "doctor", None))
        weekday = attrs.get("weekday", getattr(self.instance, "weekday", None))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if not doctor or weekday is None or not start_time or not end_time:
            return attrs
        if end_time <= start_time:
            raise serializers.ValidationError({"end_time": "End time must be later than start time."})
        overlaps = DoctorAvailability.objects.filter(
            doctor=doctor,
            weekday=weekday,
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if self.instance:
            overlaps = overlaps.exclude(pk=self.instance.pk)
        if overlaps.exists():
            raise serializers.ValidationError("This time overlaps another availability window.")
        return attrs


class ScheduleExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleException
        fields = ("id", "doctor", "date", "is_closed", "start_time", "end_time", "note")
        read_only_fields = ("id",)

    def validate(self, attrs):
        is_closed = attrs.get("is_closed", getattr(self.instance, "is_closed", True))
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if not is_closed and (not start_time or not end_time or end_time <= start_time):
            raise serializers.ValidationError(
                {"end_time": "An open exception requires valid start and end times."}
            )
        return attrs
