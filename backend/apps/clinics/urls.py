from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    DoctorAvailabilityViewSet,
    DoctorSlotsView,
    DoctorViewSet,
    ScheduleExceptionViewSet,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("availabilities", DoctorAvailabilityViewSet, basename="availability")
router.register("schedule-exceptions", ScheduleExceptionViewSet, basename="schedule-exception")

urlpatterns = [
    path("doctors/<int:doctor_id>/slots/", DoctorSlotsView.as_view(), name="doctor-slots"),
    path("", include(router.urls)),
]
