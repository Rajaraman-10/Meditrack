from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AppointmentViewSet,
    PatientAppointmentHistoryView,
    QueueEntryViewSet,
)

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("queue", QueueEntryViewSet, basename="queue")

urlpatterns = [
    path(
        "patients/<int:patient_id>/appointments/",
        PatientAppointmentHistoryView.as_view(),
        name="patient-appointment-history",
    ),
    path("", include(router.urls)),
]
