from django.urls import path

from .views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    RefreshView,
    RegistrationView,
    StaffAccountListCreateView,
    StaffAccountDetailView,
    StaffPasswordResetView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegistrationView.as_view(), name="register"),
    path("users/", StaffAccountListCreateView.as_view(), name="staff-users"),
    path("users/<int:pk>/", StaffAccountDetailView.as_view(), name="staff-user-detail"),
    path("users/<int:pk>/reset-password/", StaffPasswordResetView.as_view(), name="staff-password-reset"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
]
