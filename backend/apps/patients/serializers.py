from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.accounts.serializers import NormalizedEmailField

from .models import PatientProfile

User = get_user_model()


class PatientProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = PatientProfile
        fields = (
            "id",
            "patient_number",
            "email",
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "blood_group",
            "phone",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
            "created_at",
        )
        read_only_fields = (
            "id",
            "patient_number",
            "email",
            "first_name",
            "last_name",
            "created_at",
        )

    def validate_date_of_birth(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value


class PatientCreateSerializer(serializers.Serializer):
    email = NormalizedEmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=32, required=False, allow_blank=True)
    blood_group = serializers.CharField(max_length=3, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    emergency_contact_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )

    def validate_date_of_birth(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def create(self, validated_data):
        profile_fields = {
            key: validated_data.pop(key)
            for key in (
                "date_of_birth",
                "gender",
                "blood_group",
                "phone",
                "address",
                "emergency_contact_name",
                "emergency_contact_phone",
            )
            if key in validated_data
        }
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                role=User.Role.PATIENT,
            )
            return PatientProfile.objects.create(user=user, **profile_fields)
