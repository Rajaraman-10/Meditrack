"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/", include("apps.clinics.urls")),
    path("api/", include("apps.appointments.urls")),
    path("api/", include("apps.consultations.urls")),
    path("api/", include("apps.prescriptions.urls")),
    path("api/", include("apps.laboratory.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.dashboard.urls")),
]
