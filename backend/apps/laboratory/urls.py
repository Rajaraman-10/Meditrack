from rest_framework.routers import DefaultRouter

from .views import LabTestViewSet

router = DefaultRouter()
router.register("lab-tests", LabTestViewSet, basename="lab-test")

urlpatterns = router.urls
