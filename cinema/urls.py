"""
URL configuration for cinema project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from core.views import HealthCheckView, LivenessCheckView, ReadinessCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health checks (For load balancers, Kubernetes, monitoring)
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("ready/", ReadinessCheckView.as_view(), name="readiness-check"),
    path("live/", LivenessCheckView.as_view(), name="liveness-check"),
    # API endpoints
    path("api/", include("films.urls")),
    path("api/", include("authors.urls")),
    path("api/", include("spectators.urls")),
    path("api/", include("users.urls")),
    # Documentation OpenAPI/Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
