from django.urls import path

from .views import (
    DoctorPatientRecordView,
    DoctorPatientSearchView,
    PatientDetailView,
    PatientListCreateView,
)

app_name = "patients"

urlpatterns = [
    path("doctor-search/", DoctorPatientSearchView.as_view(), name="doctor-patient-search"),
    path("doctor-records/<int:pk>/", DoctorPatientRecordView.as_view(), name="doctor-patient-record"),
    path("", PatientListCreateView.as_view(), name="patient-list"),
    path("<int:pk>/", PatientDetailView.as_view(), name="patient-detail"),
]
