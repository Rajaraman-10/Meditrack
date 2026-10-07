from rest_framework.routers import DefaultRouter

from .views import MedicineViewSet, PrescriptionViewSet

router = DefaultRouter()
router.register("medicines", MedicineViewSet, basename="medicine")
router.register("prescriptions", PrescriptionViewSet, basename="prescription")

urlpatterns = router.urls
