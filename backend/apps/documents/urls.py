from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MedicalDocumentDownloadView, MedicalDocumentViewSet

router = DefaultRouter()
router.register("documents", MedicalDocumentViewSet, basename="medical-document")

urlpatterns = [
    path("documents/<int:pk>/download/", MedicalDocumentDownloadView.as_view(), name="medical-document-download"),
    *router.urls,
]
