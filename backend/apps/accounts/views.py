from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsAdmin
from .serializers import (
    EmailTokenObtainPairSerializer,
    RegistrationSerializer,
    StaffAccountProvisionSerializer,
    StaffAccountUpdateSerializer,
    StaffPasswordResetSerializer,
    UserSerializer,
)

User = get_user_model()


class RegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]


class StaffAccountListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.filter(
        role__in=(User.Role.DOCTOR, User.Role.RECEPTIONIST, User.Role.BILLING)
    ).select_related("doctor_profile__department").order_by(
        "role",
        "last_name",
        "first_name",
        "email",
    )
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StaffAccountProvisionSerializer
        return UserSerializer


class StaffAccountDetailView(generics.UpdateAPIView):
    queryset = User.objects.filter(
        role__in=(User.Role.DOCTOR, User.Role.RECEPTIONIST, User.Role.BILLING)
    )
    serializer_class = StaffAccountUpdateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ["patch", "options", "head"]


class StaffPasswordResetView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        staff_user = get_object_or_404(
            User.objects.filter(
                role__in=(User.Role.DOCTOR, User.Role.RECEPTIONIST, User.Role.BILLING)
            ),
            pk=pk,
        )
        serializer = StaffPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            staff_user.set_password(serializer.validated_data["password"])
            staff_user.save(update_fields=("password",))
            for outstanding_token in OutstandingToken.objects.filter(user=staff_user):
                BlacklistedToken.objects.get_or_create(token=outstanding_token)
        return Response({"detail": "Staff password reset successfully."})


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [AllowAny]


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.data.get("refresh")
        if not raw_refresh:
            raise ValidationError({"refresh": "This field is required."})

        try:
            refresh_token = RefreshToken(raw_refresh)
            token_user_id = refresh_token.get("user_id")
            if str(token_user_id) != str(request.user.pk):
                raise PermissionDenied("This refresh token does not belong to you.")
            refresh_token.blacklist()
        except TokenError as error:
            raise ValidationError({"refresh": "The refresh token is invalid or expired."}) from error

        return Response(status=status.HTTP_205_RESET_CONTENT)
