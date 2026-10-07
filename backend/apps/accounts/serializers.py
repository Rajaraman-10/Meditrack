from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.patients.models import PatientProfile

User = get_user_model()


class NormalizedEmailField(serializers.EmailField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return value.strip().lower()


class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
            "department_name",
        )
        read_only_fields = fields

    def get_department_name(self, obj):
        if obj.role != User.Role.DOCTOR:
            return None
        try:
            return obj.doctor_profile.department.name
        except User.doctor_profile.RelatedObjectDoesNotExist:
            return None


class RegistrationSerializer(serializers.ModelSerializer):
    patient_number = serializers.CharField(
        source="patient_profile.patient_number",
        read_only=True,
    )
    email = NormalizedEmailField(
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "patient_number",
        )
        read_only_fields = ("id", "role")

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data.get("first_name", ""),
                last_name=validated_data.get("last_name", ""),
                role=User.Role.PATIENT,
            )
            PatientProfile.objects.create(user=user)
            return user


class StaffAccountProvisionSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )
    role = serializers.ChoiceField(
        choices=(User.Role.RECEPTIONIST, User.Role.BILLING)
    )

    class Meta:
        model = User
        fields = ("id", "email", "password", "first_name", "last_name", "role")
        read_only_fields = ("id",)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class StaffAccountUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=(User.Role.RECEPTIONIST, User.Role.BILLING),
        required=False,
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role", "is_active")

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exclude(
            pk=self.instance.pk
        ).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate(self, attrs):
        if self.instance.role == User.Role.DOCTOR and "role" in attrs:
            raise serializers.ValidationError(
                {"role": "Doctor roles are managed through doctor management."}
            )
        return attrs


class StaffPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        return super().validate(attrs)
