"""
Health check views for monitoring and load balancer health probes.
"""

import logging
from typing import Any

from django.db import connection
from django.http import JsonResponse
from django.views import View
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check endpoint for load balancers and monitoring systems.

    Returns:
        - 200 OK: Service is healthy
        - 503 Service Unavailable: Service is unhealthy

    Response includes:
        - status: "healthy" or "unhealthy"
        - database: Database connection status
        - cache: Redis cache status
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request) -> Response:
        health_status: dict[str, Any] = {
            "status": "healthy",
            "version": "1.0.0",
            "checks": {},
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["checks"]["database"] = {"status": "up"}
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            health_status["checks"]["database"] = {"status": "down", "error": str(e)}
            health_status["status"] = "unhealthy"

        # Check cache (Redis)
        try:
            from django.core.cache import cache

            cache.set("health_check", "ok", timeout=10)
            if cache.get("health_check") == "ok":
                health_status["checks"]["cache"] = {"status": "up"}
            else:
                health_status["checks"]["cache"] = {"status": "down"}
                health_status["status"] = "unhealthy"
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            health_status["checks"]["cache"] = {"status": "down", "error": str(e)}
            health_status["status"] = "unhealthy"

        status_code = (
            status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(health_status, status=status_code)


class ReadinessCheckView(View):
    """
    Kubernetes readiness probe.
    Simple check that returns 200 if the app can handle requests.
    """

    def get(self, request) -> JsonResponse:
        return JsonResponse({"status": "ready"})


class LivenessCheckView(View):
    """
    Kubernetes liveness probe.
    Simple check that returns 200 if the app process is alive.
    """

    def get(self, request) -> JsonResponse:
        return JsonResponse({"status": "alive"})
